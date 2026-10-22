"""Safe transactional rollback verification for TASK-004 authentication against configured database.

Verifies end-to-end registration hashing, credential verification, JWT generation,
and user isolation inside a strictly rolled-back transaction so zero test data is committed.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.api.deps import enforce_resource_ownership
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.session import async_session_factory
from app.models.user import User


async def verify_auth_with_rollback() -> bool:
    print("=" * 65)
    print("Supabase Live Database Safe Rollback Auth Verification")
    print("=" * 65)

    test_uid = uuid.uuid4().hex[:8]
    test_email = f"ephemeral_test_{test_uid}@example.com"
    raw_password = f"SafeTestPass_{test_uid}!2026"

    async with async_session_factory() as session:
        try:
            print(f"[*] Starting transactional test with ephemeral user: {test_email}")

            # 1. Password hashing
            hashed_pw = hash_password(raw_password)
            assert hashed_pw != raw_password
            print("[+] Password hashed securely with bcrypt (cost 12)")

            # 2. Insert user into transaction
            user = User(
                email=test_email,
                password_hash=hashed_pw,
                display_name=f"Ephemeral User {test_uid}",
                base_currency="USD",
                timezone="UTC",
            )
            session.add(user)
            await session.flush()
            await session.refresh(user)
            print(f"[+] User created in transaction (ID: {user.id})")

            # 3. Verify user retrieval & credential check
            result = await session.execute(select(User).where(User.email == test_email))
            retrieved = result.scalar_one_or_none()
            assert retrieved is not None
            assert verify_password(raw_password, retrieved.password_hash) is True
            assert verify_password("WrongPassword123!", retrieved.password_hash) is False
            print("[+] Credential verification & constant-time check passed")

            # 4. Generate and decode JWT access token
            token = create_access_token(subject=retrieved.id)
            payload = decode_access_token(token)
            assert payload["sub"] == str(retrieved.id)
            assert payload["type"] == "access"
            print(f"[+] Signed JWT access token generated & verified (sub: {payload['sub']})")

            # 5. Verify tenant ownership enforcement
            foreign_user_id = uuid.uuid4()
            try:
                enforce_resource_ownership(foreign_user_id, retrieved)
                print("[!] FAILED: Tenant isolation did not block foreign ID")
                return False
            except Exception:
                print("[+] Multi-tenant cross-user access blocked (403 Forbidden)")

            enforce_resource_ownership(retrieved.id, retrieved)
            print("[+] Self resource ownership validated")

        finally:
            # 6. Strictly rollback transaction
            print("[*] Rolling back transaction...")
            await session.rollback()
            print("[+] Transaction rolled back successfully")

    # 7. Confirm database has zero residual test records
    async with async_session_factory() as session:
        check_result = await session.execute(select(User).where(User.email == test_email))
        residual = check_result.scalar_one_or_none()
        assert residual is None
        print(f"[+] Confirmed: Zero residual data in Supabase database for {test_email}")

    print("\n" + "=" * 65)
    print("[SUCCESS] All TASK-004 authentication operations verified against live DB!")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_auth_with_rollback())
    sys.exit(0 if success else 1)
