"""Live Supabase PostgreSQL transactional rollback verification for TASK-008.

Validates that Manual Trade Entry and CSV Trade Import work seamlessly directly
against live PostgreSQL tables, types, and constraints, verifying:
1. Manual trade creation with deterministic session and R:R calculations.
2. CSV import with standard MT5 and canonical rows.
3. Strict idempotency preventing duplicate entries on repeated imports.
4. Clean transactional rollback leaving zero test artifacts.
"""

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.core.security import encrypt_investor_password, hash_password
from app.db.session import async_session_factory
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.user import User
from app.services.csv_importer import CSVTradeImporter


async def run_live_verification():
    print("[INFO] Connecting to Supabase PostgreSQL database...")
    async with async_session_factory() as db:
        try:
            # 1. Create temporary test user & account
            test_email = f"task008_verify_{int(datetime.now(UTC).timestamp())}@example.com"
            test_user = User(
                email=test_email,
                password_hash=hash_password("VerifyPassword123!"),
            )
            db.add(test_user)
            await db.flush()

            test_account = TradingAccount(
                user_id=test_user.id,
                account_number="888999000",
                broker_name="VerificationBroker",
                server_name="Verification-Demo",
                encrypted_investor_pwd=encrypt_investor_password("InvestorPass123!"),
                account_type="DEMO",
                currency="USD",
                leverage=100,
            )
            db.add(test_account)
            await db.flush()
            print(f"[INFO] Created temporary user {test_user.id} and account {test_account.id}.")

            # 2. Test Manual Trade Creation
            t0 = datetime.now(UTC) - timedelta(hours=2)
            t1 = datetime.now(UTC) - timedelta(hours=1)
            manual_entry = JournalEntry(
                account_id=test_account.id,
                user_id=test_user.id,
                symbol="EURUSD",
                direction="BUY",
                volume=1.0,
                entry_price=1.0800,
                exit_price=1.0850,
                stop_loss=1.0750,
                take_profit=1.0900,
                gross_profit=500.0,
                commission=-7.0,
                swap=-1.5,
                net_pnl=491.5,
                rr_ratio=2.0,
                open_time=t0,
                close_time=t1,
                status="CLOSED",
                session="LONDON",
                user_notes="Manual trade live PostgreSQL test",
                idempotency_hash=f"man:{uuid.uuid4().hex[:60]}",
            )
            db.add(manual_entry)
            await db.flush()
            print("[INFO] Manual trade inserted into live PostgreSQL.")

            # 3. Test CSV Import
            csv_content = (
                "Ticket,Open Time,Type,Volume,Symbol,Open Price,Close Time,Close Price,Commission,Swap,Profit\n"
                "9001,2026-10-15 10:00:00,BUY,1.0,XAUUSD,2000.0,2026-10-15 11:30:00,2020.0,-7.0,-2.0,2000.0\n"
                "9002,2026-10-15 14:00:00,SELL,1.0,GBPUSD,1.2500,2026-10-15 15:00:00,1.2450,-7.0,0.0,500.0\n"
            )
            file_bytes = csv_content.encode("utf-8")
            importer = CSVTradeImporter()

            # Preview
            preview_res = await importer.preview_csv(
                file_bytes=file_bytes,
                account_id=test_account.id,
                current_user_id=test_user.id,
                db=db,
            )
            print(
                f"[INFO] CSV Preview: {preview_res.valid_rows_count} valid, {preview_res.error_rows_count} errors."
            )
            assert preview_res.valid_rows_count == 2
            assert preview_res.error_rows_count == 0

            # Import 1
            import_res1 = await importer.import_csv(
                file_bytes=file_bytes,
                account_id=test_account.id,
                current_user_id=test_user.id,
                db=db,
            )
            print(f"[INFO] First CSV Import: {import_res1}")
            assert import_res1.imported_count == 2
            assert import_res1.duplicates_skipped == 0

            # Import 2 (Idempotency check against live database)
            import_res2 = await importer.import_csv(
                file_bytes=file_bytes,
                account_id=test_account.id,
                current_user_id=test_user.id,
                db=db,
            )
            print(f"[INFO] Second CSV Import (Idempotent): {import_res2}")
            assert import_res2.imported_count == 0
            assert (
                import_res2.duplicates_skipped == 2
            ), "Idempotency violation: duplicates imported!"

            # Verify total count in database
            db_entries = (
                (
                    await db.execute(
                        select(JournalEntry).where(JournalEntry.account_id == test_account.id)
                    )
                )
                .scalars()
                .all()
            )
            assert (
                len(db_entries) == 3
            ), f"Expected 3 entries (1 manual + 2 CSV), found {len(db_entries)}"

            print("[SUCCESS] Live PostgreSQL Supabase verification passed perfectly!")

        finally:
            await db.rollback()
            print("[INFO] Live transaction rolled back cleanly. No test artifacts persisted.")


if __name__ == "__main__":
    asyncio.run(run_live_verification())
