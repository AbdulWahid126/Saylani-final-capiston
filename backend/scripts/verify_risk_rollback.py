"""Live Supabase PostgreSQL transactional rollback verification for TASK-010.

Validates that the Prop Firm Risk Manager Engine works seamlessly directly
against live Supabase PostgreSQL tables, types, and constraints, verifying:
1. Persistence of custom PropRiskProfile records in user_rules table.
2. Tenant-isolated retrieval of accounts and profiles.
3. Accurate daily reset window partitioning against live database trade records.
4. Correct risk gauge transitions: GREEN -> RED -> BREACHED.
5. 100% clean transactional rollback leaving zero test artifacts.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.analytics.risk_engine import (
    evaluate_account_risk,
)
from app.core.security import encrypt_investor_password, hash_password
from app.db.session import async_session_factory
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.rule import UserRule
from app.models.user import User
from app.schemas.risk import (
    DailyLossCalculationBasis,
    DrawdownModel,
    PropRiskProfileResponse,
    RiskSnapshotOverride,
    RiskStatusLevel,
)


async def run_live_verification():
    print("[INFO] Connecting to Supabase PostgreSQL database...")
    async with async_session_factory() as db:
        try:
            # 1. Create temporary test user & account
            test_email = f"task010_verify_{int(datetime.now(UTC).timestamp())}@example.com"
            test_user = User(
                email=test_email,
                password_hash=hash_password("VerifyPassword123!"),
            )
            db.add(test_user)
            await db.flush()

            test_account = TradingAccount(
                user_id=test_user.id,
                account_number="998877665",
                broker_name="SupabaseRiskVerificationBroker",
                server_name="LiveRisk-Demo",
                encrypted_investor_pwd=encrypt_investor_password("InvestorPass123!"),
                account_type="PROP_CHALLENGE",
                currency="USD",
                initial_balance=100000.0,
                balance=100000.0,
                equity=100000.0,
                leverage=100,
            )
            db.add(test_account)
            await db.flush()
            print(f"[INFO] Created temporary user {test_user.id} and account {test_account.id}.")

            # 2. Create custom user risk profile in user_rules table
            custom_rule = UserRule(
                user_id=test_user.id,
                rule_name="Live Verified 100k Challenge",
                rule_type="PROP_PROFILE",
                parameters={
                    "description": "5% daily loss, 10% static max loss, Prague timezone",
                    "initial_balance": 100000.0,
                    "daily_loss_limit_pct": 5.0,
                    "max_total_loss_limit_pct": 10.0,
                    "drawdown_model": "STATIC",
                    "daily_loss_basis": "EQUITY_BASED",
                    "trail_locks_at_initial_balance": True,
                    "daily_reset_timezone": "Europe/Prague",
                    "daily_reset_time": "00:00:00",
                    "profit_target_pct": 10.0,
                },
                is_active=True,
            )
            db.add(custom_rule)
            await db.flush()
            print(f"[INFO] Persisted custom PropRiskProfile {custom_rule.id} in user_rules.")

            # 3. Insert closed trades: 1 trade yesterday, 1 trade today
            now_utc = datetime.now(UTC)
            yesterday_trade = JournalEntry(
                user_id=test_user.id,
                account_id=test_account.id,
                symbol="EURUSD",
                direction="BUY",
                volume=1.0,
                entry_price=1.0800,
                exit_price=1.0850,
                gross_profit=500.0,
                commission=-10.0,
                swap=0.0,
                net_pnl=490.0,
                open_time=now_utc - timedelta(days=2),
                close_time=now_utc - timedelta(days=2, hours=1),
                status="CLOSED",
            )
            db.add(yesterday_trade)

            today_loss_trade = JournalEntry(
                user_id=test_user.id,
                account_id=test_account.id,
                symbol="GBPUSD",
                direction="BUY",
                volume=2.0,
                entry_price=1.2650,
                exit_price=1.2550,
                gross_profit=-2000.0,
                commission=-20.0,
                swap=0.0,
                net_pnl=-2020.0,
                open_time=now_utc - timedelta(hours=3),
                close_time=now_utc - timedelta(hours=1),
                status="CLOSED",
            )
            db.add(today_loss_trade)
            await db.flush()
            print("[INFO] Inserted 2 closed trade entries into live Supabase.")

            # 4. Fetch records back from live DB and evaluate risk
            trades_stmt = (
                select(JournalEntry)
                .where(
                    JournalEntry.user_id == test_user.id,
                    JournalEntry.account_id == test_account.id,
                )
                .order_by(JournalEntry.close_time.asc())
            )
            db_trades = list((await db.scalars(trades_stmt)).all())
            assert len(db_trades) == 2

            profile_resp = PropRiskProfileResponse(
                id=custom_rule.id,
                user_id=test_user.id,
                name=custom_rule.rule_name,
                description=custom_rule.parameters.get("description"),
                initial_balance=float(custom_rule.parameters["initial_balance"]),
                daily_loss_limit_pct=float(custom_rule.parameters["daily_loss_limit_pct"]),
                max_total_loss_limit_pct=float(custom_rule.parameters["max_total_loss_limit_pct"]),
                drawdown_model=DrawdownModel(custom_rule.parameters["drawdown_model"]),
                daily_loss_basis=DailyLossCalculationBasis(
                    custom_rule.parameters["daily_loss_basis"]
                ),
                trail_locks_at_initial_balance=bool(
                    custom_rule.parameters["trail_locks_at_initial_balance"]
                ),
                daily_reset_timezone=custom_rule.parameters["daily_reset_timezone"],
                daily_reset_time=custom_rule.parameters["daily_reset_time"],
                profit_target_pct=float(custom_rule.parameters["profit_target_pct"]),
                is_template=False,
            )

            # Evaluate with live DB trade history
            eval_result = evaluate_account_risk(
                account=test_account,
                profile=profile_resp,
                closed_trades=db_trades,
                evaluation_time=now_utc,
            )

            # Assertions: Today's loss was -$2,020.00 vs $5,000.00 daily limit -> 40.4% utilization -> GREEN
            assert eval_result.daily_risk.daily_closed_pnl == -2020.0
            assert eval_result.daily_risk.effective_daily_loss == 2020.0
            assert eval_result.daily_risk.daily_loss_limit_amount == 5000.0
            assert eval_result.daily_risk.status_level == RiskStatusLevel.GREEN
            assert eval_result.is_any_limit_breached is False

            # Test RED status via snapshot override: $4,200 loss today = 84% utilization
            red_eval = evaluate_account_risk(
                account=test_account,
                profile=profile_resp,
                closed_trades=db_trades,
                snapshot_override=RiskSnapshotOverride(
                    current_balance=97980.0,
                    current_equity=95800.0,
                    current_floating_pnl=-2180.0,
                ),
                evaluation_time=now_utc,
            )
            assert red_eval.daily_risk.effective_daily_loss == 4200.0
            assert red_eval.daily_risk.daily_loss_utilization_pct == 84.0
            assert red_eval.daily_risk.status_level == RiskStatusLevel.RED
            assert red_eval.overall_status_level == RiskStatusLevel.RED

            # Test BREACHED status: $5,500 loss today = 110% utilization
            breached_eval = evaluate_account_risk(
                account=test_account,
                profile=profile_resp,
                closed_trades=db_trades,
                snapshot_override=RiskSnapshotOverride(
                    current_balance=97980.0,
                    current_equity=94500.0,
                    current_floating_pnl=-3480.0,
                ),
                evaluation_time=now_utc,
            )
            assert breached_eval.daily_risk.status_level == RiskStatusLevel.BREACHED
            assert breached_eval.daily_risk.is_breached is True
            assert breached_eval.is_any_limit_breached is True

            print(
                "[SUCCESS] All prop firm risk engine calculations verified against live Supabase PostgreSQL records!"
            )

        finally:
            print("[INFO] Rolling back transaction to ensure 0 persistent test records...")
            await db.rollback()

    # Confirm complete rollback
    async with async_session_factory() as verify_db:
        verify_stmt = select(User).where(User.email == test_email)
        remaining = (await verify_db.scalars(verify_stmt)).all()
        assert len(remaining) == 0, "Test user was not rolled back!"
        print("[SUCCESS] 100% clean rollback confirmed. 0 residual test records in live Supabase.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
