"""Live Supabase PostgreSQL transactional rollback verification for TASK-009.

Validates that the Deterministic Financial Analytics Engine works seamlessly
directly against live Supabase PostgreSQL tables, types, and constraints, verifying:
1. Retrieval of live JournalEntry records under strict user tenancy.
2. Segregation of open and partial positions from closed statistics.
3. Deterministic calculation of metrics (Win rate, gross profit/loss, Net P&L, Profit Factor, Max Drawdown).
4. Equity curve chronological generation and high-water mark tracking.
5. Multi-dimensional breakdowns against live database data.
6. 100% clean transactional rollback leaving zero test artifacts.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.analytics.engine import (
    calculate_breakdowns,
    calculate_equity_curve,
    calculate_performance_metrics,
    extract_trade_records,
)
from app.core.security import encrypt_investor_password, hash_password
from app.db.session import async_session_factory
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.user import User


async def run_live_verification():
    print("[INFO] Connecting to Supabase PostgreSQL database...")
    async with async_session_factory() as db:
        try:
            # 1. Create temporary test user & account
            test_email = f"task009_verify_{int(datetime.now(UTC).timestamp())}@example.com"
            test_user = User(
                email=test_email,
                password_hash=hash_password("VerifyPassword123!"),
            )
            db.add(test_user)
            await db.flush()

            test_account = TradingAccount(
                user_id=test_user.id,
                account_number="777888999",
                broker_name="SupabaseLiveVerificationBroker",
                server_name="LiveVerification-Demo",
                encrypted_investor_pwd=encrypt_investor_password("InvestorPass123!"),
                account_type="LIVE",
                currency="USD",
                initial_balance=10000.0,
                balance=10000.0,
                equity=10000.0,
                leverage=100,
            )
            db.add(test_account)
            await db.flush()
            print(f"[INFO] Created temporary user {test_user.id} and account {test_account.id}.")

            # 2. Insert closed benchmark trades and 1 open trade
            base_time = datetime.now(UTC) - timedelta(days=5)
            trades_data = [
                # Trade 1: Win +$300 (net)
                {
                    "symbol": "EURUSD",
                    "direction": "BUY",
                    "volume": 1.0,
                    "entry_price": 1.0800,
                    "exit_price": 1.0830,
                    "gross_profit": 320.0,
                    "commission": -15.0,
                    "swap": -5.0,
                    "net_pnl": 300.0,
                    "open_time": base_time,
                    "close_time": base_time + timedelta(hours=2),
                    "status": "CLOSED",
                    "session": "LONDON",
                    "setup_tag": "FVG",
                },
                # Trade 2: Loss -$150 (net)
                {
                    "symbol": "EURUSD",
                    "direction": "SELL",
                    "volume": 1.0,
                    "entry_price": 1.0850,
                    "exit_price": 1.0865,
                    "gross_profit": -135.0,
                    "commission": -15.0,
                    "swap": 0.0,
                    "net_pnl": -150.0,
                    "open_time": base_time + timedelta(days=1),
                    "close_time": base_time + timedelta(days=1, hours=3),
                    "status": "CLOSED",
                    "session": "NY_AM",
                    "setup_tag": "OB",
                },
                # Trade 3: Win +$200 (net)
                {
                    "symbol": "GBPUSD",
                    "direction": "BUY",
                    "volume": 1.5,
                    "entry_price": 1.2600,
                    "exit_price": 1.2620,
                    "gross_profit": 215.0,
                    "commission": -15.0,
                    "swap": 0.0,
                    "net_pnl": 200.0,
                    "open_time": base_time + timedelta(days=2),
                    "close_time": base_time + timedelta(days=2, hours=1),
                    "status": "CLOSED",
                    "session": "LONDON",
                    "setup_tag": "FVG",
                },
                # Trade 4: Loss -$350 (net)
                {
                    "symbol": "GBPUSD",
                    "direction": "BUY",
                    "volume": 1.5,
                    "entry_price": 1.2650,
                    "exit_price": 1.2615,
                    "gross_profit": -335.0,
                    "commission": -15.0,
                    "swap": 0.0,
                    "net_pnl": -350.0,
                    "open_time": base_time + timedelta(days=3),
                    "close_time": base_time + timedelta(days=3, hours=4),
                    "status": "CLOSED",
                    "session": "NY_PM",
                    "setup_tag": "BREAKOUT",
                },
                # Trade 5: Breakeven $0.00
                {
                    "symbol": "EURUSD",
                    "direction": "BUY",
                    "volume": 0.5,
                    "entry_price": 1.0820,
                    "exit_price": 1.0820,
                    "gross_profit": 10.0,
                    "commission": -10.0,
                    "swap": 0.0,
                    "net_pnl": 0.0,
                    "open_time": base_time + timedelta(days=4),
                    "close_time": base_time + timedelta(days=4, hours=1),
                    "status": "CLOSED",
                    "session": "ASIA",
                    "setup_tag": "SCALP",
                },
                # Open trade (floating)
                {
                    "symbol": "XAUUSD",
                    "direction": "BUY",
                    "volume": 0.1,
                    "entry_price": 2650.0,
                    "exit_price": None,
                    "gross_profit": 0.0,
                    "commission": -2.0,
                    "swap": 0.0,
                    "net_pnl": 0.0,
                    "open_time": datetime.now(UTC),
                    "close_time": None,
                    "status": "OPEN",
                    "session": "NY_AM",
                    "setup_tag": "SWING",
                },
            ]

            for d in trades_data:
                entry = JournalEntry(
                    user_id=test_user.id,
                    account_id=test_account.id,
                    symbol=d["symbol"],
                    direction=d["direction"],
                    volume=d["volume"],
                    entry_price=d["entry_price"],
                    exit_price=d["exit_price"],
                    gross_profit=d["gross_profit"],
                    commission=d["commission"],
                    swap=d["swap"],
                    net_pnl=d["net_pnl"],
                    open_time=d["open_time"],
                    close_time=d["close_time"],
                    status=d["status"],
                    session=d["session"],
                    setup_tag=d["setup_tag"],
                )
                db.add(entry)
            await db.flush()
            print("[INFO] Inserted 5 closed benchmark trades and 1 open trade into live Supabase.")

            # 3. Query entries back from live database
            stmt = (
                select(JournalEntry)
                .where(
                    JournalEntry.user_id == test_user.id,
                    JournalEntry.account_id == test_account.id,
                )
                .order_by(JournalEntry.close_time.asc())
            )
            res = await db.scalars(stmt)
            db_entries = list(res.all())
            assert len(db_entries) == 6, f"Expected 6 entries, got {len(db_entries)}"

            # 4. Run analytics engine on live database records
            closed_records, open_count = extract_trade_records(db_entries)
            assert len(closed_records) == 5, f"Expected 5 closed trades, got {len(closed_records)}"
            assert open_count == 1, f"Expected 1 open trade, got {open_count}"

            metrics = calculate_performance_metrics(
                closed_records,
                initial_balance=test_account.initial_balance,
                currency=test_account.currency,
                open_trades_count=open_count,
            )

            # Mathematical assertions
            assert metrics.total_trades == 5
            assert metrics.winning_trades == 2
            assert metrics.losing_trades == 2
            assert metrics.breakeven_trades == 1
            assert metrics.win_rate == 40.0
            assert metrics.loss_rate == 40.0
            assert metrics.breakeven_rate == 20.0
            assert metrics.gross_profit == 500.0
            assert metrics.gross_loss == 500.0
            assert metrics.net_pnl == 0.0
            assert metrics.profit_factor == 1.00
            assert metrics.max_drawdown_monetary == 350.0
            assert metrics.max_drawdown_percentage == 3.38
            assert metrics.open_trades_count == 1

            # Equity curve assertion
            eq_curve = calculate_equity_curve(
                closed_records,
                initial_balance=test_account.initial_balance,
                currency=test_account.currency,
            )
            assert len(eq_curve.points) == 6
            assert eq_curve.points[0].equity == 10000.0
            assert eq_curve.points[1].equity == 10300.0
            assert eq_curve.points[2].equity == 10150.0
            assert eq_curve.points[3].equity == 10350.0
            assert eq_curve.points[4].equity == 10000.0
            assert eq_curve.points[5].equity == 10000.0

            # Breakdowns assertion
            breakdowns = calculate_breakdowns(closed_records)
            assert len(breakdowns.by_symbol) == 2
            assert breakdowns.by_symbol[0].category in ["EURUSD", "GBPUSD"]

            print(
                "[SUCCESS] All deterministic analytics verified against live Supabase PostgreSQL records!"
            )

        finally:
            print("[INFO] Rolling back transaction to ensure 0 persistent test records...")
            await db.rollback()

    # 5. Confirm complete rollback
    async with async_session_factory() as verify_db:
        verify_stmt = select(User).where(User.email == test_email)
        remaining = (await verify_db.scalars(verify_stmt)).all()
        assert len(remaining) == 0, "Test user was not rolled back!"
        print("[SUCCESS] 100% clean rollback confirmed. 0 residual test records in live Supabase.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
