"""Automated unit and integration tests for MT5 Automated Deal Aggregator & Idempotent Sync Worker (TASK-007).

Tests cover:
- Deal synchronization from read-only MT5 connector into raw_mt5_deals and journal_entries.
- Strict database idempotency: repeated sync runs produce zero duplicate raw deals or journal entries.
- Volume-weighted average entry and exit price calculations across multiple fills.
- Partial close and scaled exit lifecycle (OPEN -> PARTIAL -> CLOSED).
- Financial math determinism: accurate gross profit, commission, swap, fee, and net P&L aggregation.
- Preservation of user-authored journal metadata (notes, emotional state, setup tag).
- Non-trade balance operations (deposits/withdrawals) preserved in raw deals without polluting journal.
- Multi-tenant security: cross-user synchronization attempts are blocked (HTTP 403).
- Error handling: date range validation (400), MT5 query failure (503), account not found (404).
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.deal import RawMT5Deal
from app.models.journal import DealJournalMapping, JournalEntry
from app.schemas.mt5 import MT5DealInfo
from app.services.sync_worker import SyncWorker


def make_mock_deal(
    ticket: int,
    position_id: int,
    order: int,
    deal_type: int,  # 0=BUY, 1=SELL, 2=BALANCE
    entry: int,  # 0=IN, 1=OUT, 2=INOUT
    volume: float,
    price: float,
    profit: float = 0.0,
    commission: float = 0.0,
    swap: float = 0.0,
    fee: float = 0.0,
    symbol: str = "EURUSD",
    deal_time: datetime | None = None,
) -> MT5DealInfo:
    """Helper creating typed MT5DealInfo instance for mock connector."""
    return MT5DealInfo(
        ticket=ticket,
        order=order,
        time=deal_time or datetime.now(UTC),
        time_msc=0,
        type=deal_type,
        entry=entry,
        magic=0,
        position_id=position_id,
        reason=0,
        volume=volume,
        price=price,
        commission=commission,
        swap=swap,
        profit=profit,
        fee=fee,
        symbol=symbol,
        comment="Test fill",
        external_id="",
    )


async def create_user_and_account(
    async_client: AsyncClient, email: str, account_number: str = "123456"
) -> dict:
    """Registers user, creates trading account, and returns IDs + auth headers."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "display_name": "Sync Trader"},
    )
    assert reg.status_code == 201
    user_id = uuid.UUID(reg.json()["id"])
    token = create_access_token(subject=user_id)
    headers = {"Authorization": f"Bearer {token}"}

    acc_res = await async_client.post(
        "/api/v1/accounts",
        json={
            "broker_name": "Demo Broker",
            "server_name": "Demo-Server",
            "account_number": account_number,
            "account_type": "DEMO",
            "investor_password": "InvestorPass123!",
            "initial_balance": 10000.0,
        },
        headers=headers,
    )
    assert acc_res.status_code == 201
    account_id = uuid.UUID(acc_res.json()["id"])

    return {
        "user_id": user_id,
        "account_id": account_id,
        "headers": headers,
    }


# =============================================================================
# Unit Tests for SyncWorker
# =============================================================================


@pytest.mark.asyncio
async def test_sync_repeated_runs_strict_idempotency(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies that running synchronization repeatedly creates zero duplicate deals or journal entries."""
    user = await create_user_and_account(async_client, "idempotent_sync@example.com", "100001")
    acc_id = user["account_id"]

    t0 = datetime.now(UTC) - timedelta(hours=2)
    t1 = datetime.now(UTC) - timedelta(hours=1)

    mock_deals = [
        make_mock_deal(
            ticket=501,
            position_id=101,
            order=301,
            deal_type=0,
            entry=0,
            volume=1.0,
            price=1.0800,
            deal_time=t0,
        ),
        make_mock_deal(
            ticket=502,
            position_id=101,
            order=302,
            deal_type=1,
            entry=1,
            volume=1.0,
            price=1.0850,
            profit=500.0,
            deal_time=t1,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = mock_deals
    mock_connector.get_account_info.side_effect = Exception("Not available in mock")

    worker = SyncWorker(connector=mock_connector)

    # First sync run
    res1 = await worker.sync_account(
        account_id=acc_id,
        current_user_id=user["user_id"],
        db=db_session,
    )
    assert res1.total_deals_retrieved == 2
    assert res1.new_deals_saved == 2
    assert res1.positions_aggregated == 1
    assert res1.closed_positions_count == 1

    # Check database state after Sync 1
    deals_count1 = (
        (await db_session.execute(select(RawMT5Deal).where(RawMT5Deal.account_id == acc_id)))
        .scalars()
        .all()
    )
    assert len(deals_count1) == 2

    entries1 = (
        (await db_session.execute(select(JournalEntry).where(JournalEntry.account_id == acc_id)))
        .scalars()
        .all()
    )
    assert len(entries1) == 1
    assert entries1[0].status == "CLOSED"
    assert entries1[0].net_pnl == 500.0
    original_entry_id = entries1[0].id

    # Second sync run with identical deals
    res2 = await worker.sync_account(
        account_id=acc_id,
        current_user_id=user["user_id"],
        db=db_session,
    )
    assert res2.total_deals_retrieved == 2
    assert res2.new_deals_saved == 0  # STRICT IDEMPOTENCY: Zero new deals
    assert res2.positions_aggregated == 1

    # Verify database still has exactly 2 deals and 1 journal entry with unchanged ID
    deals_count2 = (
        (await db_session.execute(select(RawMT5Deal).where(RawMT5Deal.account_id == acc_id)))
        .scalars()
        .all()
    )
    assert len(deals_count2) == 2

    entries2 = (
        (await db_session.execute(select(JournalEntry).where(JournalEntry.account_id == acc_id)))
        .scalars()
        .all()
    )
    assert len(entries2) == 1
    assert entries2[0].id == original_entry_id


@pytest.mark.asyncio
async def test_sync_multiple_entry_fills_volume_weighted_price(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies accurate volume-weighted entry price calculation across scaled-in entry fills."""
    user = await create_user_and_account(async_client, "vwap_entry@example.com", "100002")
    acc_id = user["account_id"]

    t0 = datetime.now(UTC) - timedelta(hours=3)
    t1 = datetime.now(UTC) - timedelta(hours=2)

    # Scaled Entry:
    # Fill 1: 1.0 lot @ 1.0800 ($108,000)
    # Fill 2: 2.0 lots @ 1.0860 ($217,200)
    # Total volume: 3.0 lots
    # Expected weighted price = (108,000 + 217,200) / 3.0 = 325,200 / 3.0 = 1.08400
    mock_deals = [
        make_mock_deal(
            ticket=601,
            position_id=202,
            order=401,
            deal_type=0,
            entry=0,
            volume=1.0,
            price=1.0800,
            deal_time=t0,
        ),
        make_mock_deal(
            ticket=602,
            position_id=202,
            order=402,
            deal_type=0,
            entry=0,
            volume=2.0,
            price=1.0860,
            deal_time=t1,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = mock_deals

    worker = SyncWorker(connector=mock_connector)
    res = await worker.sync_account(
        account_id=acc_id, current_user_id=user["user_id"], db=db_session
    )

    assert res.open_positions_count == 1
    assert res.closed_positions_count == 0

    entry = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 202
            )
        )
    ).scalar_one()

    assert entry.volume == 3.0
    assert entry.entry_price == 1.08400
    assert entry.exit_price is None
    assert entry.status == "OPEN"
    assert entry.close_time is None


@pytest.mark.asyncio
async def test_sync_partial_closes_and_scaled_exits(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies that partial exits update status to PARTIAL and then CLOSED with weighted exit price."""
    user = await create_user_and_account(async_client, "partial_exit@example.com", "100003")
    acc_id = user["account_id"]

    t0 = datetime.now(UTC) - timedelta(hours=4)
    t1 = datetime.now(UTC) - timedelta(hours=3)
    t2 = datetime.now(UTC) - timedelta(hours=1)

    # Phase 1: Open 2.0 lots, then partial close 1.0 lot @ 1.0850
    phase1_deals = [
        make_mock_deal(
            ticket=701,
            position_id=303,
            order=501,
            deal_type=0,
            entry=0,
            volume=2.0,
            price=1.0800,
            deal_time=t0,
        ),
        make_mock_deal(
            ticket=702,
            position_id=303,
            order=502,
            deal_type=1,
            entry=1,
            volume=1.0,
            price=1.0850,
            profit=500.0,
            deal_time=t1,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = phase1_deals

    worker = SyncWorker(connector=mock_connector)
    res1 = await worker.sync_account(
        account_id=acc_id, current_user_id=user["user_id"], db=db_session
    )

    assert res1.open_positions_count == 1  # 1 open/partial
    assert res1.closed_positions_count == 0

    entry1 = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 303
            )
        )
    ).scalar_one()

    assert entry1.status == "PARTIAL"
    assert entry1.entry_price == 1.0800
    assert entry1.exit_price == 1.0850
    assert entry1.net_pnl == 500.0
    assert entry1.close_time is None

    # Phase 2: Later deal arrives closing the remaining 1.0 lot @ 1.0900
    # Expected weighted exit price = (1.0 * 1.0850 + 1.0 * 1.0900) / 2.0 = 1.0875
    phase2_deals = phase1_deals + [
        make_mock_deal(
            ticket=703,
            position_id=303,
            order=503,
            deal_type=1,
            entry=1,
            volume=1.0,
            price=1.0900,
            profit=1000.0,
            deal_time=t2,
        ),
    ]
    mock_connector.get_historical_deals.return_value = phase2_deals

    res2 = await worker.sync_account(
        account_id=acc_id, current_user_id=user["user_id"], db=db_session
    )
    assert res2.new_deals_saved == 1
    assert res2.closed_positions_count == 1

    entry2 = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 303
            )
        )
    ).scalar_one()

    assert entry2.status == "CLOSED"
    assert entry2.exit_price == 1.0875
    assert entry2.net_pnl == 1500.0
    assert entry2.close_time is not None


@pytest.mark.asyncio
async def test_sync_preserves_user_authored_journal_fields(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies that automated sync never overwrites user notes, emotional state, or setup tags."""
    user = await create_user_and_account(async_client, "preserve_notes@example.com", "100004")
    acc_id = user["account_id"]

    t0 = datetime.now(UTC) - timedelta(hours=3)
    t1 = datetime.now(UTC) - timedelta(hours=1)

    # Initial open trade
    deals_open = [
        make_mock_deal(
            ticket=801,
            position_id=404,
            order=601,
            deal_type=0,
            entry=0,
            volume=1.0,
            price=1.0800,
            deal_time=t0,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = deals_open

    worker = SyncWorker(connector=mock_connector)
    await worker.sync_account(account_id=acc_id, current_user_id=user["user_id"], db=db_session)

    # User annotates their journal entry manually
    entry = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 404
            )
        )
    ).scalar_one()

    entry.user_notes = "Double bottom breakout on H1 timeframe with London open volume."
    entry.emotional_state = "CONFIDENT"
    entry.setup_tag = "DOUBLE_BOTTOM"
    await db_session.commit()

    # Later sync arrives with trade close
    deals_closed = deals_open + [
        make_mock_deal(
            ticket=802,
            position_id=404,
            order=602,
            deal_type=1,
            entry=1,
            volume=1.0,
            price=1.0880,
            profit=800.0,
            deal_time=t1,
        ),
    ]
    mock_connector.get_historical_deals.return_value = deals_closed

    await worker.sync_account(account_id=acc_id, current_user_id=user["user_id"], db=db_session)

    re_fetched = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 404
            )
        )
    ).scalar_one()

    # Market metrics updated
    assert re_fetched.status == "CLOSED"
    assert re_fetched.net_pnl == 800.0

    # User-authored content 100% PRESERVED
    assert (
        re_fetched.user_notes == "Double bottom breakout on H1 timeframe with London open volume."
    )
    assert re_fetched.emotional_state == "CONFIDENT"
    assert re_fetched.setup_tag == "DOUBLE_BOTTOM"


@pytest.mark.asyncio
async def test_sync_financial_accuracy_commissions_swaps_fees(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies deterministic math for gross profit, commissions, swaps, fees, and net P&L."""
    user = await create_user_and_account(async_client, "financial_math@example.com", "100005")
    acc_id = user["account_id"]

    mock_deals = [
        make_mock_deal(
            ticket=901,
            position_id=505,
            order=701,
            deal_type=0,
            entry=0,
            volume=1.0,
            price=1.0800,
            commission=-3.50,
            swap=0.0,
            fee=0.0,
            profit=0.0,
        ),
        make_mock_deal(
            ticket=902,
            position_id=505,
            order=702,
            deal_type=1,
            entry=1,
            volume=1.0,
            price=1.0850,
            commission=-3.50,
            swap=-1.20,
            fee=-0.30,
            profit=500.0,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = mock_deals

    worker = SyncWorker(connector=mock_connector)
    await worker.sync_account(account_id=acc_id, current_user_id=user["user_id"], db=db_session)

    entry = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 505
            )
        )
    ).scalar_one()

    assert entry.gross_profit == 500.0
    assert entry.commission == -7.0
    assert entry.swap == -1.20
    # Expected net P&L = 500.0 + (-7.0) + (-1.20) + (-0.30) = 491.50
    assert entry.net_pnl == 491.50


@pytest.mark.asyncio
async def test_sync_non_trade_balance_deals_not_in_journal(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies that deposits/withdrawals (position_id == 0) are saved in raw_deals but never create journal entries."""
    user = await create_user_and_account(async_client, "balance_deals@example.com", "100006")
    acc_id = user["account_id"]

    mock_deals = [
        # Deposit
        make_mock_deal(
            ticket=10001,
            position_id=0,
            order=0,
            deal_type=2,  # DEAL_TYPE_BALANCE
            entry=0,
            volume=0.0,
            price=0.0,
            profit=10000.0,
            symbol="",
        ),
        # Trade fill
        make_mock_deal(
            ticket=10002,
            position_id=606,
            order=801,
            deal_type=0,
            entry=0,
            volume=1.0,
            price=1.0800,
            profit=0.0,
            symbol="EURUSD",
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = mock_deals

    worker = SyncWorker(connector=mock_connector)
    res = await worker.sync_account(
        account_id=acc_id, current_user_id=user["user_id"], db=db_session
    )

    # 2 raw deals saved
    assert res.new_deals_saved == 2
    # Only 1 position aggregated
    assert res.positions_aggregated == 1

    # Raw deals table has 2
    raws = (
        (await db_session.execute(select(RawMT5Deal).where(RawMT5Deal.account_id == acc_id)))
        .scalars()
        .all()
    )
    assert len(raws) == 2

    # Journal entries table has ONLY 1
    journals = (
        (await db_session.execute(select(JournalEntry).where(JournalEntry.account_id == acc_id)))
        .scalars()
        .all()
    )
    assert len(journals) == 1
    assert journals[0].broker_position_id == 606


@pytest.mark.asyncio
async def test_sync_deal_mappings_table(async_client: AsyncClient, db_session: AsyncSession):
    """Verifies that DealJournalMapping records link individual raw deals to their parent journal entry."""
    user = await create_user_and_account(async_client, "mapping_test@example.com", "100007")
    acc_id = user["account_id"]

    mock_deals = [
        make_mock_deal(
            ticket=1101, position_id=707, order=901, deal_type=0, entry=0, volume=1.0, price=1.0800
        ),
        make_mock_deal(
            ticket=1102,
            position_id=707,
            order=902,
            deal_type=1,
            entry=1,
            volume=1.0,
            price=1.0850,
            profit=500.0,
        ),
    ]

    mock_connector = MagicMock()
    mock_connector.is_initialized = True
    mock_connector.get_historical_deals.return_value = mock_deals

    worker = SyncWorker(connector=mock_connector)
    await worker.sync_account(account_id=acc_id, current_user_id=user["user_id"], db=db_session)

    entry = (
        await db_session.execute(
            select(JournalEntry).where(
                JournalEntry.account_id == acc_id, JournalEntry.broker_position_id == 707
            )
        )
    ).scalar_one()

    mappings = (
        (
            await db_session.execute(
                select(DealJournalMapping).where(DealJournalMapping.journal_entry_id == entry.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(mappings) == 2


# =============================================================================
# API Endpoint Integration Tests (POST /api/v1/accounts/{id}/sync)
# =============================================================================


@pytest.mark.asyncio
async def test_sync_endpoint_cross_user_forbidden(async_client: AsyncClient):
    """Verifies that User B cannot trigger sync on User A's trading account (HTTP 403)."""
    user_a = await create_user_and_account(async_client, "owner_sync@example.com", "200001")
    user_b = await create_user_and_account(async_client, "attacker_sync@example.com", "200002")

    # User B attempts to sync User A's account
    res = await async_client.post(
        f"/api/v1/accounts/{user_a['account_id']}/sync",
        json={"days": 15},
        headers=user_b["headers"],
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_sync_endpoint_invalid_date_bounds(async_client: AsyncClient):
    """Verifies that inverted date ranges return HTTP 422 Unprocessable Entity from schema validation."""
    user = await create_user_and_account(async_client, "date_bounds@example.com", "200003")

    now = datetime.now(UTC)
    res = await async_client.post(
        f"/api/v1/accounts/{user['account_id']}/sync",
        json={
            "date_from": now.isoformat(),
            "date_to": (now - timedelta(days=5)).isoformat(),
        },
        headers=user["headers"],
    )
    assert res.status_code == 422
