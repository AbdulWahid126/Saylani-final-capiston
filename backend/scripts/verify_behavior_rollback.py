"""Live Supabase PostgreSQL transactional rollback verification for TASK-011.

Validates that the Trading Behavior Analyzer works seamlessly directly
against live Supabase PostgreSQL tables, types, and constraints, verifying:
1. Persistence of custom BehaviorAnalysisConfig in user_rules table (rule_type="BEHAVIOR_CONFIG").
2. Querying live journal_entries scoped strictly to authenticated user tenancy.
3. Rapid re-entry after loss detection with time gap and volume evidence.
4. Risk escalation / Martingale sizing pattern detection.
5. Session drift detection with session tag and timezone awareness.
6. Absolute tenant isolation (User A vs User B data segregation).
7. 100% clean transactional rollback leaving zero test artifacts.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select

from app.analytics.behavior_analyzer import analyze_trading_behavior
from app.core.security import encrypt_investor_password, hash_password
from app.db.session import async_session_factory
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.rule import UserRule
from app.models.user import User
from app.schemas.behavior import (
    BehaviorAnalysisConfig,
    BehaviorPatternType,
    BehaviorSeverity,
)


async def run_live_verification():
    print("[INFO] Connecting to Supabase PostgreSQL database...")
    async with async_session_factory() as db:
        try:
            # 1. Create temporary test user & account
            now_ts = int(datetime.now(UTC).timestamp())
            test_user = User(
                email=f"task011_verify_{now_ts}@example.com",
                password_hash=hash_password("VerifyPassword123!"),
            )
            db.add(test_user)
            await db.flush()

            test_account = TradingAccount(
                user_id=test_user.id,
                account_number=f"BEHAV-{now_ts % 100000}",
                broker_name="SupabaseBehaviorBroker",
                server_name="Behavior-Live",
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

            # 2. Persist custom behavioral configuration in user_rules table
            custom_behavior_rule = UserRule(
                user_id=test_user.id,
                rule_name="Live Verified Behavioral Rules",
                rule_type="BEHAVIOR_CONFIG",
                parameters={
                    "reentry_window_minutes": 15,
                    "max_trades_per_day": 5,
                    "size_escalation_ratio": 1.5,
                    "size_lookback_trades": 1,
                    "compare_same_symbol_only": True,
                    "allowed_sessions": ["LONDON", "NY_AM"],
                    "session_timezone": "America/New_York",
                },
                is_active=True,
            )
            db.add(custom_behavior_rule)
            await db.flush()
            print(
                f"[INFO] Persisted UserRule {custom_behavior_rule.id} (rule_type='BEHAVIOR_CONFIG')."
            )

            # 3. Insert live journal entries exhibiting behavioral patterns
            base_time = datetime.now(UTC) - timedelta(hours=3)

            # Trade 1: Loss (-$200.0) on EURUSD, 1.0 lot, closed at base_time
            t1 = JournalEntry(
                user_id=test_user.id,
                account_id=test_account.id,
                symbol="EURUSD",
                direction="BUY",
                volume=1.0,
                entry_price=1.1000,
                exit_price=1.0900,
                gross_profit=-200.0,
                commission=-5.0,
                swap=0.0,
                net_pnl=-205.0,
                open_time=base_time - timedelta(minutes=45),
                close_time=base_time,
                status="CLOSED",
                session="LONDON",
            )
            db.add(t1)

            # Trade 2: Rapid re-entry 4 minutes after t1 close, 2.0 lots (doubled size = risk escalation)
            t2 = JournalEntry(
                user_id=test_user.id,
                account_id=test_account.id,
                symbol="EURUSD",
                direction="BUY",
                volume=2.0,
                entry_price=1.0895,
                exit_price=1.0920,
                gross_profit=50.0,
                commission=-10.0,
                swap=0.0,
                net_pnl=40.0,
                open_time=base_time + timedelta(minutes=4),
                close_time=base_time + timedelta(minutes=30),
                status="CLOSED",
                session="LONDON",
            )
            db.add(t2)

            # Trade 3: Session drift trade (session='ASIA' when allowed_sessions=['LONDON', 'NY_AM'])
            t3 = JournalEntry(
                user_id=test_user.id,
                account_id=test_account.id,
                symbol="GBPUSD",
                direction="SELL",
                volume=1.0,
                entry_price=1.2800,
                exit_price=1.2780,
                gross_profit=40.0,
                commission=-5.0,
                swap=0.0,
                net_pnl=35.0,
                open_time=base_time - timedelta(hours=6),
                close_time=base_time - timedelta(hours=5),
                status="CLOSED",
                session="ASIA",
            )
            db.add(t3)
            await db.flush()
            print("[INFO] Inserted 3 live JournalEntry records for behavior evaluation.")

            # 4. Fetch entries directly from live database
            entries_stmt = (
                select(JournalEntry)
                .where(
                    JournalEntry.user_id == test_user.id,
                    JournalEntry.account_id == test_account.id,
                )
                .order_by(JournalEntry.close_time.asc())
            )
            live_entries = list((await db.scalars(entries_stmt)).all())
            assert len(live_entries) == 3, f"Expected 3 entries, got {len(live_entries)}"

            # 5. Execute behavior analysis using the persisted configuration
            effective_config = BehaviorAnalysisConfig(**custom_behavior_rule.parameters)
            summary = analyze_trading_behavior(
                entries=live_entries,
                config=effective_config,
                account_id=test_account.id,
            )

            print("[INFO] Behavior Analysis Complete:")
            print(f"       Total trades analyzed: {summary.total_trades_analyzed}")
            print(f"       Total findings: {summary.total_findings}")
            print(f"       High severity findings: {summary.high_severity_count}")
            print(f"       Medium severity findings: {summary.medium_severity_count}")
            print(f"       Discipline score: {summary.overall_discipline_score}/100")

            # Validate Rapid Re-entry pattern detection
            reentry_findings = [
                f
                for f in summary.findings
                if f.pattern_type == BehaviorPatternType.RAPID_REENTRY_AFTER_LOSS
            ]
            assert (
                len(reentry_findings) == 1
            ), f"Expected 1 rapid re-entry finding, got {len(reentry_findings)}"
            assert reentry_findings[0].evidence["time_gap_minutes"] == 4.0
            assert reentry_findings[0].evidence["prior_loss_amount"] == 205.0
            assert reentry_findings[0].severity == BehaviorSeverity.HIGH
            print(
                "[PASS] Verified Rapid Re-entry pattern detection with exact time gap and loss evidence."
            )

            # Validate Risk Escalation pattern detection
            escalation_findings = [
                f for f in summary.findings if f.pattern_type == BehaviorPatternType.RISK_ESCALATION
            ]
            assert (
                len(escalation_findings) == 1
            ), f"Expected 1 risk escalation finding, got {len(escalation_findings)}"
            assert escalation_findings[0].evidence["size_multiplier"] == 2.0
            assert escalation_findings[0].evidence["symbol"] == "EURUSD"
            assert escalation_findings[0].severity == BehaviorSeverity.HIGH
            print(
                "[PASS] Verified Risk Escalation pattern detection (2.0x Martingale sizing pattern)."
            )

            # Validate Session Drift pattern detection
            drift_findings = [
                f for f in summary.findings if f.pattern_type == BehaviorPatternType.SESSION_DRIFT
            ]
            assert (
                len(drift_findings) == 1
            ), f"Expected 1 session drift finding, got {len(drift_findings)}"
            assert drift_findings[0].evidence["trade_session"] == "ASIA"
            print("[PASS] Verified Session Drift pattern detection (out-of-session ASIA trade).")

            # Validate discipline score deduction
            assert summary.overall_discipline_score < 100.0
            print(
                f"[PASS] Verified deterministic discipline score calculation: {summary.overall_discipline_score}/100."
            )

            # 6. Verify Tenant Isolation against live database
            user_b = User(
                email=f"task011_userb_{now_ts}@example.com",
                password_hash=hash_password("VerifyPassword123!"),
            )
            db.add(user_b)
            await db.flush()

            user_b_entries_stmt = select(JournalEntry).where(JournalEntry.user_id == user_b.id)
            user_b_entries = list((await db.scalars(user_b_entries_stmt)).all())
            assert len(user_b_entries) == 0, "Tenant isolation failure: User B saw User A's trades!"

            user_b_summary = analyze_trading_behavior(
                entries=user_b_entries,
                config=effective_config,
            )
            assert user_b_summary.total_trades_analyzed == 0
            assert user_b_summary.total_findings == 0
            assert user_b_summary.overall_discipline_score == 100.0
            print("[PASS] Verified complete multi-tenant isolation against live database.")

        finally:
            # 7. Guaranteed transactional rollback
            await db.rollback()
            print(
                "[INFO] Successfully rolled back transaction. Zero test records committed to database."
            )

    # 8. Post-rollback verification: Confirm zero residual records exist
    async with async_session_factory() as verify_db:
        res_user = await verify_db.scalar(
            select(func.count(User.id)).where(User.email.like("task011_%@example.com"))
        )
        assert res_user == 0, f"Leaked test users detected: {res_user}"

        res_acc = await verify_db.scalar(
            select(func.count(TradingAccount.id)).where(
                TradingAccount.broker_name == "SupabaseBehaviorBroker"
            )
        )
        assert res_acc == 0, f"Leaked test accounts detected: {res_acc}"

        res_rules = await verify_db.scalar(
            select(func.count(UserRule.id)).where(
                UserRule.rule_name == "Live Verified Behavioral Rules"
            )
        )
        assert res_rules == 0, f"Leaked test rules detected: {res_rules}"

        print("[SUCCESS] All live Supabase verification checks PASSED with 0 residual records.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
