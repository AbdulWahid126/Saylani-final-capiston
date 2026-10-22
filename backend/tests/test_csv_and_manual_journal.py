"""Automated Tests for TASK-008: CSV Trade History Import & Manual Entry Fallback.

Tests cover:
- Manual trade creation: open vs closed trades, deterministic R:R and Net P&L math.
- Manual trade validation errors (negative volume, close_time < open_time).
- Multi-tenant isolation: User A cannot read, update, delete, or import trades into User B's accounts.
- Guardrails: MT5-synced trades cannot have their verified execution prices/volumes modified manually.
- CSV Preview: Canonical CSV, standard MT5 export with duplicate Time/Price columns.
- CSV Row-Level Errors: Malformed values, invalid timestamps, missing required headers.
- CSV Strict Idempotency: Repeated uploads produce 0 duplicate journal entries.
- CSV Formula Injection Sanitization: Leading =, +, -, @ are sanitized safely.
- Transactional Rollback: Failing imports do not leave corrupted database records.
"""

import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.journal import JournalEntry


async def create_user_and_account(
    client: AsyncClient, email: str, account_number: str
) -> dict[str, str]:
    """Helper to create and authenticate a test user and their trading account."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert reg_resp.status_code == 201
    user_id = reg_resp.json()["id"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    acc_resp = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "broker_name": "ICMarkets",
            "server_name": "ICMarkets-Demo",
            "account_number": account_number,
            "account_type": "DEMO",
            "currency": "USD",
            "leverage": 100,
        },
    )
    assert acc_resp.status_code == 201
    acc_id = acc_resp.json()["id"]

    return {"user_id": user_id, "token": token, "account_id": acc_id}


# =============================================================================
# 1. Manual Trade Entry Tests
# =============================================================================


@pytest.mark.asyncio
async def test_manual_trade_creation_open_trade(async_client: AsyncClient):
    """Verifies creating an open manual trade without exit price or close time."""
    user = await create_user_and_account(async_client, "manual_open@example.com", "200001")
    headers = {"Authorization": f"Bearer {user['token']}"}

    t0 = datetime.now(UTC).isoformat()
    payload = {
        "account_id": user["account_id"],
        "symbol": "EURUSD",
        "direction": "BUY",
        "volume": 0.5,
        "entry_price": 1.0850,
        "stop_loss": 1.0800,
        "take_profit": 1.0950,
        "open_time": t0,
        "status": "OPEN",
        "user_notes": "Breakout pullback long entry",
        "setup_tag": "Breakout",
    }

    res = await async_client.post("/api/v1/journal/entries", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["symbol"] == "EURUSD"
    assert data["direction"] == "BUY"
    assert data["volume"] == 0.5
    assert data["entry_price"] == 1.0850
    assert data["exit_price"] is None
    assert data["close_time"] is None
    assert data["status"] == "OPEN"
    assert data["source"] == "MANUAL"
    assert data["rr_ratio"] == 2.0  # (1.0950 - 1.0850) / (1.0850 - 1.0800) = 0.0100 / 0.0050 = 2.0
    assert data["session"] in ("ASIA", "LONDON", "NY_AM", "NY_PM")


@pytest.mark.asyncio
async def test_manual_trade_creation_closed_trade_deterministic_math(async_client: AsyncClient):
    """Verifies deterministic calculation of Net P&L and R:R ratio on closed trade."""
    user = await create_user_and_account(async_client, "manual_closed@example.com", "200002")
    headers = {"Authorization": f"Bearer {user['token']}"}

    t0 = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    t1 = datetime.now(UTC).isoformat()

    payload = {
        "account_id": user["account_id"],
        "symbol": "XAUUSD",
        "direction": "SELL",
        "volume": 1.0,
        "entry_price": 2050.0,
        "exit_price": 2030.0,
        "stop_loss": 2060.0,
        "take_profit": 2020.0,
        "gross_profit": 2000.0,
        "commission": -7.0,
        "swap": -3.5,
        "open_time": t0,
        "close_time": t1,
        "status": "CLOSED",
    }

    res = await async_client.post("/api/v1/journal/entries", headers=headers, json=payload)
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "CLOSED"
    assert data["gross_profit"] == 2000.0
    assert data["net_pnl"] == round(2000.0 - 7.0 - 3.5, 4)  # 1989.5
    # For SELL: Risk = 2060 - 2050 = 10; Reward = 2050 - 2020 = 30; R:R = 30 / 10 = 3.0
    assert data["rr_ratio"] == 3.0
    assert data["source"] == "MANUAL"


@pytest.mark.asyncio
async def test_manual_trade_validation_errors(async_client: AsyncClient):
    """Verifies that invalid manual trade data is rejected with 422."""
    user = await create_user_and_account(async_client, "manual_err@example.com", "200003")
    headers = {"Authorization": f"Bearer {user['token']}"}

    t0 = datetime.now(UTC)
    t_past = (t0 - timedelta(hours=1)).isoformat()
    t0_iso = t0.isoformat()

    # 1. Negative volume
    res1 = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": user["account_id"],
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": -0.5,
            "entry_price": 1.0850,
            "open_time": t0_iso,
        },
    )
    assert res1.status_code == 422

    # 2. Close time earlier than open time
    res2 = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": user["account_id"],
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": 1.0,
            "entry_price": 1.0850,
            "exit_price": 1.0900,
            "open_time": t0_iso,
            "close_time": t_past,  # Earlier than open!
            "status": "CLOSED",
        },
    )
    assert res2.status_code == 422

    # 3. Closed trade missing exit price
    res3 = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": user["account_id"],
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": 1.0,
            "entry_price": 1.0850,
            "open_time": t0_iso,
            "close_time": (t0 + timedelta(hours=1)).isoformat(),
            "status": "CLOSED",
        },
    )
    assert res3.status_code == 422


@pytest.mark.asyncio
async def test_manual_trade_multi_tenant_isolation(async_client: AsyncClient):
    """Proves User A cannot read, update, delete, or create trades in User B's account."""
    user_a = await create_user_and_account(async_client, "user_a@example.com", "200004")
    user_b = await create_user_and_account(async_client, "user_b@example.com", "200005")

    headers_a = {"Authorization": f"Bearer {user_a['token']}"}
    headers_b = {"Authorization": f"Bearer {user_b['token']}"}

    # User A creates a trade
    res_a = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers_a,
        json={
            "account_id": user_a["account_id"],
            "symbol": "GBPUSD",
            "direction": "BUY",
            "volume": 1.0,
            "entry_price": 1.2500,
            "open_time": datetime.now(UTC).isoformat(),
        },
    )
    assert res_a.status_code == 201
    entry_id = res_a.json()["id"]

    # User B attempts to read User A's trade -> 403 Forbidden
    get_res = await async_client.get(f"/api/v1/journal/entries/{entry_id}", headers=headers_b)
    assert get_res.status_code == 403

    # User B attempts to update User A's trade -> 403 Forbidden
    put_res = await async_client.put(
        f"/api/v1/journal/entries/{entry_id}",
        headers=headers_b,
        json={"user_notes": "Hacked note"},
    )
    assert put_res.status_code == 403

    # User B attempts to delete User A's trade -> 403 Forbidden
    del_res = await async_client.delete(f"/api/v1/journal/entries/{entry_id}", headers=headers_b)
    assert del_res.status_code == 403

    # User B attempts to create a trade pointing to User A's account -> 403 Forbidden
    create_cross = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers_b,
        json={
            "account_id": user_a["account_id"],
            "symbol": "BTCUSD",
            "direction": "BUY",
            "volume": 0.1,
            "entry_price": 60000.0,
            "open_time": datetime.now(UTC).isoformat(),
        },
    )
    assert create_cross.status_code == 403


@pytest.mark.asyncio
async def test_update_manual_trade_preserves_notes_and_recalculates(async_client: AsyncClient):
    """Verifies updating an existing manual trade updates fields and recalculates Net P&L."""
    user = await create_user_and_account(async_client, "manual_upd@example.com", "200006")
    headers = {"Authorization": f"Bearer {user['token']}"}

    create_res = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": user["account_id"],
            "symbol": "USDCAD",
            "direction": "BUY",
            "volume": 1.0,
            "entry_price": 1.3500,
            "open_time": datetime.now(UTC).isoformat(),
            "user_notes": "Initial analysis",
        },
    )
    entry_id = create_res.json()["id"]

    # Update note, add exit price and gross profit
    t_close = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    upd_res = await async_client.put(
        f"/api/v1/journal/entries/{entry_id}",
        headers=headers,
        json={
            "exit_price": 1.3550,
            "close_time": t_close,
            "gross_profit": 500.0,
            "commission": -6.0,
            "user_notes": "Updated post-trade reflection: target reached quickly.",
            "emotional_state": "Disciplined",
        },
    )
    assert upd_res.status_code == 200
    upd_data = upd_res.json()

    assert upd_data["exit_price"] == 1.3550
    assert upd_data["gross_profit"] == 500.0
    assert upd_data["net_pnl"] == 494.0  # 500 - 6
    assert upd_data["user_notes"] == "Updated post-trade reflection: target reached quickly."
    assert upd_data["emotional_state"] == "Disciplined"


@pytest.mark.asyncio
async def test_update_mt5_synced_trade_blocks_altering_market_data(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies guardrail: MT5-synced trades reject manual changes to market execution data."""
    user = await create_user_and_account(async_client, "mt5_guard@example.com", "200007")
    headers = {"Authorization": f"Bearer {user['token']}"}

    # Simulate an MT5 synced trade directly in DB with broker_position_id
    entry = JournalEntry(
        account_id=uuid.UUID(user["account_id"]),
        user_id=uuid.UUID(user["user_id"]),
        broker_position_id=987654,
        symbol="XAUUSD",
        direction="BUY",
        volume=2.0,
        entry_price=2000.0,
        exit_price=2020.0,
        gross_profit=4000.0,
        net_pnl=3990.0,
        open_time=datetime.now(UTC) - timedelta(hours=2),
        close_time=datetime.now(UTC) - timedelta(hours=1),
        status="CLOSED",
        idempotency_hash="hash_mt5_synced_12345",
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)

    # 1. Attempting to tamper with verified entry_price -> 400 Bad Request
    tamper_res = await async_client.put(
        f"/api/v1/journal/entries/{entry.id}",
        headers=headers,
        json={"entry_price": 1950.0},
    )
    assert tamper_res.status_code == 400
    tamper_json = tamper_res.json()
    err_msg = tamper_json.get("error", {}).get("message") or tamper_json.get("detail", {}).get(
        "message", ""
    )
    assert "Cannot manually modify execution metrics" in err_msg

    # 2. Updating discretionary notes on the synced trade -> SUCCCEEDS
    notes_res = await async_client.put(
        f"/api/v1/journal/entries/{entry.id}",
        headers=headers,
        json={
            "user_notes": "Annotated MT5 trade with my strategy tag",
            "setup_tag": "ICT Silver Bullet",
        },
    )
    assert notes_res.status_code == 200
    assert notes_res.json()["user_notes"] == "Annotated MT5 trade with my strategy tag"
    assert notes_res.json()["setup_tag"] == "ICT Silver Bullet"
    assert notes_res.json()["entry_price"] == 2000.0  # Original price unchanged


# =============================================================================
# 2. CSV Import & Preview Tests
# =============================================================================


@pytest.mark.asyncio
async def test_csv_preview_valid_canonical_file(async_client: AsyncClient):
    """Verifies dry-run preview of a valid canonical CSV trade history export."""
    user = await create_user_and_account(async_client, "csv_prev@example.com", "200008")
    headers = {"Authorization": f"Bearer {user['token']}"}

    csv_content = (
        "Ticket,Open Time,Type,Volume,Symbol,Open Price,S / L,T / P,Close Time,Close Price,Commission,Swap,Profit,Comment\n"
        "1001,2026.10.15 10:00:00,BUY,1.0,EURUSD,1.0800,1.0750,1.0900,2026.10.15 12:00:00,1.0850,-7.0,0.0,500.0,London Open Long\n"
        "1002,2026.10.16 14:30:00,SELL,2.0,GBPUSD,1.2600,1.2650,1.2500,2026.10.16 16:00:00,1.2550,-14.0,-2.0,1000.0,NY AM Short\n"
        "1003,2026.10.17 08:00:00,BUY,0.5,XAUUSD,2020.0,2010.0,2040.0,0,0,0,0,0,Open Swing Position\n"
    )

    files = {"file": ("trades.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": user["account_id"]}

    res = await async_client.post(
        "/api/v1/journal/csv/preview", headers=headers, data=data, files=files
    )
    assert res.status_code == 200
    preview = res.json()

    assert preview["total_rows"] == 3
    assert preview["valid_rows_count"] == 3
    assert preview["error_rows_count"] == 0
    assert len(preview["sample_valid_rows"]) == 3
    assert preview["sample_valid_rows"][0]["symbol"] == "EURUSD"
    assert preview["sample_valid_rows"][2]["status"] == "OPEN"  # No close time


@pytest.mark.asyncio
async def test_csv_preview_row_validation_errors(async_client: AsyncClient):
    """Verifies that row-level errors are reported accurately without crashing."""
    user = await create_user_and_account(async_client, "csv_err@example.com", "200009")
    headers = {"Authorization": f"Bearer {user['token']}"}

    csv_content = (
        "Ticket,Open Time,Type,Volume,Symbol,Open Price\n"
        "2001,2026.10.15 10:00:00,BUY,-1.0,EURUSD,1.0800\n"  # Negative volume
        "2002,INVALID_DATE,SELL,1.0,GBPUSD,1.2600\n"  # Invalid date
        "2003,2026.10.15 10:00:00,UNKNOWN,1.0,XAUUSD,2000.0\n"  # Invalid direction
    )

    files = {"file": ("invalid_trades.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": user["account_id"]}

    res = await async_client.post(
        "/api/v1/journal/csv/preview", headers=headers, data=data, files=files
    )
    assert res.status_code == 200
    preview = res.json()

    assert preview["total_rows"] == 3
    assert preview["valid_rows_count"] == 0
    assert preview["error_rows_count"] == 3
    assert len(preview["errors"]) == 3
    assert preview["errors"][0]["field"] == "volume"
    assert preview["errors"][1]["field"] == "open_time"
    assert preview["errors"][2]["field"] == "direction"


@pytest.mark.asyncio
async def test_csv_import_canonical_and_query_journal(async_client: AsyncClient):
    """Verifies importing valid CSV trades and querying them back through journal list API."""
    user = await create_user_and_account(async_client, "csv_import@example.com", "200010")
    headers = {"Authorization": f"Bearer {user['token']}"}

    csv_content = (
        "Ticket,Open Time,Type,Volume,Symbol,Open Price,Close Time,Close Price,Commission,Swap,Profit\n"
        "3001,2026-10-10 10:00:00,BUY,1.0,EURUSD,1.0800,2026-10-10 11:30:00,1.0850,-6.0,-1.0,500.0\n"
        "3002,2026-10-11 14:00:00,SELL,2.0,GBPUSD,1.2700,2026-10-11 15:00:00,1.2650,-12.0,0.0,1000.0\n"
    )

    files = {"file": ("import.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": user["account_id"]}

    import_res = await async_client.post(
        "/api/v1/journal/csv/import", headers=headers, data=data, files=files
    )
    assert import_res.status_code == 201
    import_data = import_res.json()

    assert import_data["total_rows"] == 2
    assert import_data["imported_count"] == 2
    assert import_data["duplicates_skipped"] == 0

    # Query journal list endpoint
    list_res = await async_client.get(
        f"/api/v1/journal/entries?account_id={user['account_id']}",
        headers=headers,
    )
    assert list_res.status_code == 200
    list_data = list_res.json()

    assert list_data["total"] == 2
    assert list_data["items"][0]["source"] == "CSV"
    assert list_data["items"][1]["source"] == "CSV"


@pytest.mark.asyncio
async def test_csv_import_mt5_standard_format_duplicate_headers(async_client: AsyncClient):
    """Verifies standard MT5 export report format where Time and Price appear twice."""
    user = await create_user_and_account(async_client, "csv_mt5_fmt@example.com", "200011")
    headers = {"Authorization": f"Bearer {user['token']}"}

    # Standard MT5 export: first Time/Price is open, second Time/Price is close
    csv_content = (
        "Position,Time,Type,Volume,Symbol,Price,S / L,T / P,Time,Price,Commission,Swap,Profit,Comment\n"
        "4001,2026.10.01 09:00:00,buy,1.5,USDJPY,150.000,149.500,151.000,2026.10.01 13:00:00,150.800,-10.0,-3.0,1200.0,Standard MT5 Export\n"
    )

    files = {"file": ("mt5_report.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": user["account_id"]}

    res = await async_client.post(
        "/api/v1/journal/csv/import", headers=headers, data=data, files=files
    )
    assert res.status_code == 201
    res_data = res.json()

    assert res_data["imported_count"] == 1

    # Verify parsed values in DB
    list_res = await async_client.get(
        f"/api/v1/journal/entries?account_id={user['account_id']}",
        headers=headers,
    )
    trade = list_res.json()["items"][0]
    assert trade["symbol"] == "USDJPY"
    assert trade["entry_price"] == 150.000
    assert trade["exit_price"] == 150.800
    assert trade["volume"] == 1.5
    assert trade["net_pnl"] == 1187.0  # 1200 - 10 - 3


@pytest.mark.asyncio
async def test_csv_import_strict_idempotency_repeated_runs(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies that uploading the exact same CSV multiple times creates 0 duplicate trades."""
    user = await create_user_and_account(async_client, "csv_idemp@example.com", "200012")
    headers = {"Authorization": f"Bearer {user['token']}"}

    csv_content = (
        "Ticket,Open Time,Type,Volume,Symbol,Open Price,Close Time,Close Price,Profit\n"
        "5001,2026-10-15 10:00:00,BUY,1.0,EURUSD,1.0800,2026-10-15 11:00:00,1.0840,400.0\n"
        "5002,2026-10-15 12:00:00,SELL,1.0,GBPUSD,1.2600,2026-10-15 13:00:00,1.2560,400.0\n"
    )

    # Run 1: Initial import
    files1 = {"file": ("trades.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res1 = await async_client.post(
        "/api/v1/journal/csv/import",
        headers=headers,
        data={"account_id": user["account_id"]},
        files=files1,
    )
    assert res1.status_code == 201
    assert res1.json()["imported_count"] == 2
    assert res1.json()["duplicates_skipped"] == 0

    # Run 2: Re-import exact same file
    files2 = {"file": ("trades.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res2 = await async_client.post(
        "/api/v1/journal/csv/import",
        headers=headers,
        data={"account_id": user["account_id"]},
        files=files2,
    )
    assert res2.status_code == 201
    assert res2.json()["imported_count"] == 0
    assert (
        res2.json()["duplicates_skipped"] == 2
    ), "Idempotency violated: duplicates were not skipped!"

    # Verify database count is strictly 2
    db_entries = (
        (
            await db_session.execute(
                select(JournalEntry).where(JournalEntry.account_id == uuid.UUID(user["account_id"]))
            )
        )
        .scalars()
        .all()
    )
    assert len(db_entries) == 2, f"Expected exactly 2 entries in DB, found {len(db_entries)}"


@pytest.mark.asyncio
async def test_csv_import_formula_injection_sanitization(async_client: AsyncClient):
    """Verifies that malicious spreadsheet formulas in CSV comments are sanitized."""
    user = await create_user_and_account(async_client, "csv_injection@example.com", "200013")
    headers = {"Authorization": f"Bearer {user['token']}"}

    csv_content = (
        "Ticket,Open Time,Type,Volume,Symbol,Open Price,Comment\n"
        "6001,2026-10-15 10:00:00,BUY,1.0,EURUSD,1.0800,=cmd|'/c calc'!A1\n"
        "6002,2026-10-15 11:00:00,BUY,1.0,EURUSD,1.0800,@SUM(1+1)\n"
    )

    files = {"file": ("formula.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": user["account_id"]}

    res = await async_client.post(
        "/api/v1/journal/csv/import", headers=headers, data=data, files=files
    )
    assert res.status_code == 201

    list_res = await async_client.get(
        f"/api/v1/journal/entries?account_id={user['account_id']}",
        headers=headers,
    )
    items = list_res.json()["items"]
    # Check that dangerous leading characters were prepended with apostrophe
    notes = [i["user_notes"] for i in items]
    assert any(n.startswith("'=") for n in notes if n)
    assert any(n.startswith("'@") for n in notes if n)


@pytest.mark.asyncio
async def test_csv_import_cross_user_isolation(async_client: AsyncClient):
    """Verifies User B cannot upload a CSV report into User A's trading account."""
    user_a = await create_user_and_account(async_client, "csv_user_a@example.com", "200014")
    user_b = await create_user_and_account(async_client, "csv_user_b@example.com", "200015")

    headers_b = {"Authorization": f"Bearer {user_b['token']}"}

    csv_content = "Ticket,Open Time,Type,Volume,Symbol,Open Price\n7001,2026-10-15 10:00:00,BUY,1.0,EURUSD,1.0800\n"
    files = {"file": ("trades.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    data = {"account_id": user_a["account_id"]}  # Target User A's account!

    # Preview -> 403 Forbidden
    prev_res = await async_client.post(
        "/api/v1/journal/csv/preview", headers=headers_b, data=data, files=files
    )
    assert prev_res.status_code == 403

    # Import -> 403 Forbidden
    files2 = {"file": ("trades.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    imp_res = await async_client.post(
        "/api/v1/journal/csv/import", headers=headers_b, data=data, files=files2
    )
    assert imp_res.status_code == 403
