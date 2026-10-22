"""
Supabase PostgreSQL live transaction rollback verification for TASK-007.

Validates that SyncWorker interacts properly with real PostgreSQL types,
constraints, tables, and transactional rollback without leaving test artifacts.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.core.security import encrypt_investor_password, hash_password
from app.db.session import async_session_factory
from app.models.account import TradingAccount
from app.models.deal import RawMT5Deal
from app.models.journal import DealJournalMapping, JournalEntry
from app.models.user import User
from app.services.sync_worker import SyncWorker


def make_mock_deal(
    ticket: int,
    position_id: int,
    order: int,
    deal_type: int,
    entry: int,
    volume: float,
    price: float,
    profit: float = 0.0,
    commission: float = 0.0,
    swap: float = 0.0,
    fee: float = 0.0,
    symbol: str = "XAUUSD",
    deal_time: datetime | None = None,
) -> SimpleNamespace:
    t = deal_time or datetime.now(UTC)
    return SimpleNamespace(
        ticket=ticket,
        order=order,
        time=t,
        time_msc=int(t.timestamp() * 1000),
        type=deal_type,
        entry=entry,
        entry_type="IN" if entry == 0 else "OUT",
        position_id=position_id,
        volume=volume,
        price=price,
        profit=profit,
        commission=commission,
        swap=swap,
        fee=fee,
        symbol=symbol,
        comment="Live Verification Deal",
    )


async def run_live_verification():
    print("[INFO] Connecting to Supabase PostgreSQL database...")
    async with async_session_factory() as db:
        try:
            # 1. Create temporary test user & account
            test_email = f"sync_verify_{int(datetime.now(UTC).timestamp())}@example.com"
            test_user = User(
                email=test_email,
                password_hash=hash_password("TestPassword123!"),
            )
            db.add(test_user)
            await db.flush()

            test_account = TradingAccount(
                user_id=test_user.id,
                account_number="777888999",
                broker_name="MockBroker",
                server_name="MockBroker-Demo",
                encrypted_investor_pwd=encrypt_investor_password("MockInvestorPass123!"),
                account_type="DEMO",
                currency="USD",
                leverage=100,
            )
            db.add(test_account)
            await db.flush()
            print(
                f"[INFO] Created temporary test user {test_user.id} and account {test_account.id}."
            )

            # 2. Mock MT5 connector returns 2 deals for 1 position
            base_time = datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC)
            deal1 = make_mock_deal(
                ticket=80001,
                position_id=70001,
                order=90001,
                deal_type=0,  # BUY
                entry=0,  # IN
                volume=1.0,
                price=2000.0,
                profit=0.0,
                commission=-3.5,
                swap=0.0,
                deal_time=base_time,
            )
            deal2 = make_mock_deal(
                ticket=80002,
                position_id=70001,
                order=90002,
                deal_type=1,  # SELL
                entry=1,  # OUT
                volume=1.0,
                price=2020.0,
                profit=200.0,
                commission=-3.5,
                swap=-1.2,
                deal_time=base_time + timedelta(hours=2),
            )

            mock_conn = MagicMock()
            mock_conn.is_initialized = True
            mock_conn.get_historical_deals.return_value = [deal1, deal2]
            mock_conn.get_account_info.return_value = None

            worker = SyncWorker(connector=mock_conn)

            # First sync run
            summary1 = await worker.sync_account(
                account_id=test_account.id,
                current_user_id=test_user.id,
                db=db,
                date_from=datetime(2026, 10, 1, tzinfo=UTC),
                date_to=datetime(2026, 10, 20, tzinfo=UTC),
            )
            print(f"[INFO] First Sync: {summary1}")
            assert summary1.total_deals_retrieved == 2
            assert summary1.new_deals_saved == 2
            assert summary1.positions_aggregated == 1
            assert summary1.closed_positions_count == 1

            # Verify in DB
            db_deals = (
                (
                    await db.execute(
                        select(RawMT5Deal).where(RawMT5Deal.account_id == test_account.id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(db_deals) == 2, f"Expected 2 raw deals, got {len(db_deals)}"

            db_entry = (
                await db.execute(
                    select(JournalEntry).where(JournalEntry.account_id == test_account.id)
                )
            ).scalar_one()
            assert db_entry is not None
            assert db_entry.status == "CLOSED"
            assert round(db_entry.net_pnl, 2) == round(200.0 - 7.0 - 1.2, 2)
            assert db_entry.symbol == "XAUUSD"

            db_mappings = (
                (
                    await db.execute(
                        select(DealJournalMapping).where(
                            DealJournalMapping.journal_entry_id == db_entry.id
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(db_mappings) == 2

            # Edit user note to verify it is preserved across subsequent sync runs
            db_entry.user_notes = "Important user discretionary note: Trend following execution."
            await db.flush()

            # Second sync run (Idempotency check)
            summary2 = await worker.sync_account(
                account_id=test_account.id,
                current_user_id=test_user.id,
                db=db,
                date_from=datetime(2026, 10, 1, tzinfo=UTC),
                date_to=datetime(2026, 10, 20, tzinfo=UTC),
            )
            print(f"[INFO] Second Sync (Idempotent): {summary2}")
            assert summary2.total_deals_retrieved == 2
            assert summary2.new_deals_saved == 0, "Idempotency violation: deals re-inserted!"
            assert summary2.positions_aggregated == 1
            assert summary2.closed_positions_count == 1

            # Verify user notes were preserved
            await db.refresh(db_entry)
            assert (
                db_entry.user_notes
                == "Important user discretionary note: Trend following execution."
            ), "User notes were overwritten during sync!"

            print("[SUCCESS] Live PostgreSQL Supabase transaction verification passed perfectly!")
        finally:
            await db.rollback()
            print("[INFO] Live transaction rolled back cleanly. No test artifacts persisted.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
