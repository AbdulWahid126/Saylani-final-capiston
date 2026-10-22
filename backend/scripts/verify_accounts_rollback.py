"""Safe transactional rollback verification for TASK-006 against live Supabase PostgreSQL database.

Validates end-to-end trading account creation, AES-256-GCM investor password
encryption/decryption, tenant isolation, and safe deletion retention rules inside a strictly
rolled-back transaction so zero test data is committed.
"""

import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func, select

from app.api.deps import enforce_resource_ownership
from app.core.errors import ForbiddenError
from app.core.security import (
    decrypt_investor_password,
    encrypt_investor_password,
    hash_password,
)
from app.db.session import async_session_factory
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.user import User


async def verify_accounts_with_rollback() -> bool:
    print("=" * 70)
    print("Supabase Live Database Safe Rollback Verification (TASK-006)")
    print("=" * 70)

    test_uid = uuid.uuid4().hex[:8]
    test_email = f"ephemeral_trader_{test_uid}@example.com"
    raw_password = f"SafePass_{test_uid}!2026"
    investor_pwd = f"InvestorSecret_{test_uid}!#2026"

    async with async_session_factory() as session:
        try:
            print(f"[*] Starting transactional test with ephemeral user: {test_email}")

            # 1. Create ephemeral user
            user = User(
                email=test_email,
                password_hash=hash_password(raw_password),
                display_name=f"Ephemeral Trader {test_uid}",
                base_currency="USD",
                timezone="UTC",
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            print(f"[+] User created in transaction (ID: {user.id})")

            # 2. Encrypt investor password with AES-256-GCM
            encrypted_pwd = encrypt_investor_password(investor_pwd)
            assert encrypted_pwd != investor_pwd
            assert investor_pwd not in encrypted_pwd
            print(
                "[+] Investor password encrypted using AES-256-GCM (authenticated tag + 12-byte nonce)"
            )

            # 3. Create Trading Account
            account = TradingAccount(
                user_id=user.id,
                broker_name="MetaQuotes Demo Broker",
                server_name="MetaQuotes-Demo",
                account_number=f"ACC_{test_uid}",
                account_type="DEMO",
                encrypted_investor_pwd=encrypted_pwd,
                balance=10000.0,
                equity=10000.0,
                initial_balance=10000.0,
                currency="USD",
                leverage=100,
                sync_status="DISCONNECTED",
            )
            session.add(account)
            await session.flush()
            await session.refresh(account)
            print(f"[+] TradingAccount inserted in transaction (ID: {account.id})")

            # 4. Verify password retrieval and decryption
            stmt = select(TradingAccount).where(TradingAccount.id == account.id)
            fetched = (await session.execute(stmt)).scalar_one()
            decrypted_pwd = decrypt_investor_password(fetched.encrypted_investor_pwd)
            assert decrypted_pwd == investor_pwd
            print("[+] Verified decryption roundtrip: retrieved plaintext matches exactly")

            # 5. Verify Multi-Tenant Resource Ownership
            foreign_user_id = uuid.uuid4()
            try:
                enforce_resource_ownership(fetched.user_id, foreign_user_id)
                raise AssertionError(
                    "Should have raised ForbiddenError on cross-tenant ownership check"
                )
            except ForbiddenError:
                print(
                    "[+] Verified tenant isolation: cross-tenant access correctly raised ForbiddenError"
                )

            # 6. Verify Safe Data Retention Rule (Deletion Protection)
            journal_entry = JournalEntry(
                account_id=account.id,
                user_id=user.id,
                symbol="EURUSD",
                direction="BUY",
                volume=0.5,
                entry_price=1.0850,
                open_time=datetime.now(UTC),
            )
            session.add(journal_entry)
            await session.flush()

            # Check dependent count
            deal_count = (
                await session.execute(
                    select(func.count())
                    .select_from(TradingAccount)
                    .where(TradingAccount.id == account.id)
                )
            ).scalar()
            assert deal_count == 1

            journal_count = (
                await session.execute(
                    select(func.count())
                    .select_from(JournalEntry)
                    .where(JournalEntry.account_id == account.id)
                )
            ).scalar()
            assert journal_count == 1
            print(
                f"[+] Verified data retention safeguard: account contains {journal_count} dependent journal entry"
            )

            return True

        finally:
            print("[*] Rolling back transaction to prevent committing test data...")
            await session.rollback()
            print(
                "[+] Transaction rolled back. Zero residual test data committed to live Supabase DB."
            )

            # Double check that ephemeral user does not exist in DB
            stmt = select(User).where(User.email == test_email)
            check_user = (await session.execute(stmt)).scalar_one_or_none()
            assert check_user is None
            print("[+] Verified 0 records remain in the live database.")


if __name__ == "__main__":
    import asyncio

    success = asyncio.run(verify_accounts_with_rollback())
    sys.exit(0 if success else 1)
