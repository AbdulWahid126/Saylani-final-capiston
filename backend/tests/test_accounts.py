"""Automated unit and integration tests for Trading Account CRUD & Credential Encryption (TASK-006).

Tests cover:
- AES-256-GCM authenticated encryption/decryption roundtrip, nonce uniqueness, key validation.
- Cryptographic failure modes: wrong key, tampered ciphertext, malformed payloads.
- Full CRUD API lifecycle: create, list, retrieve, update, and safe delete.
- Strict multi-tenant user isolation (User A vs User B boundaries).
- Password redaction verification across API responses and model serialization.
- Safe deletion policy guarding against accidental loss of historical trades.
"""

import base64
import os
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decrypt_investor_password,
    encrypt_investor_password,
    validate_encryption_key,
)
from app.models.account import TradingAccount
from app.models.journal import JournalEntry

# =============================================================================
# 1. Cryptographic Security Tests (AES-256-GCM)
# =============================================================================


def test_encryption_roundtrip():
    """Verifies that plaintext investor passwords encrypt and decrypt accurately."""
    plaintext = "SecureInvestorPass#2026!"
    encrypted = encrypt_investor_password(plaintext)

    assert encrypted != plaintext
    # Result must be valid base64
    raw_payload = base64.b64decode(encrypted)
    assert len(raw_payload) >= 28  # 12-byte nonce + min 16-byte tag

    decrypted = decrypt_investor_password(encrypted)
    assert decrypted == plaintext


def test_encryption_unique_nonces():
    """Verifies that encrypting identical plaintexts generates unique ciphertexts."""
    plaintext = "IdenticalSecretPassword"
    encrypted1 = encrypt_investor_password(plaintext)
    encrypted2 = encrypt_investor_password(plaintext)

    # Different nonces must yield different ciphertexts
    assert encrypted1 != encrypted2
    assert decrypt_investor_password(encrypted1) == plaintext
    assert decrypt_investor_password(encrypted2) == plaintext


def test_decryption_wrong_key():
    """Verifies that decrypting with an incorrect key fails authentication."""
    key1 = os.urandom(32)
    key2 = os.urandom(32)

    encrypted = encrypt_investor_password("MyPassword123", key=key1)

    with pytest.raises(ValueError) as exc_info:
        decrypt_investor_password(encrypted, key=key2)

    assert "authentication tag verification failed" in str(exc_info.value)


def test_decryption_tampered_ciphertext():
    """Verifies that any modification to ciphertext or auth tag is detected and rejected."""
    plaintext = "TamperProofPassword"
    encrypted = encrypt_investor_password(plaintext)

    # Decode, modify one byte in ciphertext, re-encode
    raw = bytearray(base64.b64decode(encrypted))
    raw[-1] ^= 0x01  # Flip one bit in authentication tag
    tampered = base64.b64encode(raw).decode("utf-8")

    with pytest.raises(ValueError) as exc_info:
        decrypt_investor_password(tampered)

    assert "authentication tag verification failed" in str(exc_info.value)


def test_decryption_malformed_payload():
    """Verifies that non-base64 or truncated payloads raise ValueError."""
    with pytest.raises(ValueError) as exc_b64:
        decrypt_investor_password("NotValidBase64@@@!!!")
    assert "Malformed encrypted payload" in str(exc_b64.value)

    with pytest.raises(ValueError) as exc_short:
        # Valid base64 but only 10 bytes (too short for 12-byte nonce + 16-byte tag)
        short_payload = base64.b64encode(b"short10byt").decode("utf-8")
        decrypt_investor_password(short_payload)
    assert "Invalid encrypted payload size" in str(exc_short.value)


def test_validate_encryption_key_length():
    """Verifies key length validation (must be 32 bytes)."""
    # 16-byte key -> invalid
    with pytest.raises(ValueError) as exc_16:
        validate_encryption_key("too_short_16byte")
    assert "expected 32 bytes" in str(exc_16.value)

    # Valid 32-byte raw string
    raw_32 = "a" * 32
    assert validate_encryption_key(raw_32) == raw_32.encode("utf-8")

    # Valid 32-byte base64
    b64_32 = base64.b64encode(b"b" * 32).decode("utf-8")
    assert validate_encryption_key(b64_32) == b"b" * 32


def test_validate_encryption_key_production_guard(monkeypatch):
    """Verifies that default dev key is strictly forbidden in production mode."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")

    with pytest.raises(ValueError) as exc_info:
        validate_encryption_key("ZGV2XzMyX2J5dGVfYWVzX2djbV9zZWNyZXRfa2V5MTI=")

    assert "Default development ENCRYPTION_KEY is strictly forbidden" in str(exc_info.value)


# =============================================================================
# Helper function to create authenticated users in test database
# =============================================================================


async def create_test_user_auth(
    async_client: AsyncClient, email: str, password: str = "TestPass123!"
) -> dict:
    """Helper creating a user via registration and returning user_id + auth headers."""
    reg_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "Test Trader"},
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    user_id = uuid.UUID(user_data["id"])
    token = create_access_token(subject=user_id)
    return {"user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


# =============================================================================
# 2. Trading Account CRUD & Multi-Tenant Isolation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_account_success_and_password_redaction(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies account creation, investor password encryption, and zero-exposure response."""
    user = await create_test_user_auth(async_client, "account_owner@example.com")

    payload = {
        "broker_name": "IC Markets",
        "server_name": "ICMarketsSC-Demo01",
        "account_number": "12345678",
        "account_type": "DEMO",
        "investor_password": "SuperSecretInvestorPass123!",
        "initial_balance": 10000.0,
        "currency": "USD",
        "leverage": 500,
    }
    res = await async_client.post("/api/v1/accounts", json=payload, headers=user["headers"])
    assert res.status_code == 201

    data = res.json()
    assert data["broker_name"] == "IC Markets"
    assert data["account_number"] == "12345678"
    assert data["has_investor_password"] is True
    assert data["balance"] == 10000.0
    assert data["leverage"] == 500

    # CRITICAL SECURITY CHECK: Password must NEVER appear in API response
    assert "investor_password" not in data
    assert "encrypted_investor_pwd" not in data
    assert "SuperSecretInvestorPass123!" not in str(res.content)

    account_id = uuid.UUID(data["id"])

    # Check database record: must be encrypted, not plaintext
    stmt = select(TradingAccount).where(TradingAccount.id == account_id)
    account = (await db_session.execute(stmt)).scalar_one()

    assert account.encrypted_investor_pwd is not None
    assert "SuperSecretInvestorPass123!" not in account.encrypted_investor_pwd
    # Decrypt verifying authenticity
    decrypted = decrypt_investor_password(account.encrypted_investor_pwd)
    assert decrypted == "SuperSecretInvestorPass123!"


@pytest.mark.asyncio
async def test_create_duplicate_account_conflict(async_client: AsyncClient):
    """Verifies that registering the same account number on the same server returns 409 Conflict."""
    user = await create_test_user_auth(async_client, "dup_trader@example.com")

    payload = {
        "broker_name": "RoboForex",
        "server_name": "RoboForex-ECN",
        "account_number": "99988877",
        "account_type": "LIVE",
        "initial_balance": 5000.0,
    }
    res1 = await async_client.post("/api/v1/accounts", json=payload, headers=user["headers"])
    assert res1.status_code == 201

    # Second creation with identical account_number and server_name for this user
    res2 = await async_client.post("/api/v1/accounts", json=payload, headers=user["headers"])
    assert res2.status_code == 409
    assert "already registered" in res2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_create_account_validation_errors(async_client: AsyncClient):
    """Verifies validation rules on account creation."""
    user = await create_test_user_auth(async_client, "validation_trader@example.com")

    # Invalid account type
    bad_type = {
        "broker_name": "Broker",
        "server_name": "Server",
        "account_number": "123",
        "account_type": "INVALID_TYPE",
    }
    res = await async_client.post("/api/v1/accounts", json=bad_type, headers=user["headers"])
    assert res.status_code == 422

    # Negative initial balance
    bad_balance = {
        "broker_name": "Broker",
        "server_name": "Server",
        "account_number": "123",
        "initial_balance": -100.0,
    }
    res2 = await async_client.post("/api/v1/accounts", json=bad_balance, headers=user["headers"])
    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_multi_tenant_list_and_read_isolation(async_client: AsyncClient):
    """Verifies strict tenant isolation: User A cannot see or fetch User B's accounts."""
    user_a = await create_test_user_auth(async_client, "user_a@example.com")
    user_b = await create_test_user_auth(async_client, "user_b@example.com")

    # User A creates Account A
    res_a = await async_client.post(
        "/api/v1/accounts",
        json={
            "broker_name": "UserA Broker",
            "server_name": "UserA-Server",
            "account_number": "111111",
        },
        headers=user_a["headers"],
    )
    assert res_a.status_code == 201
    account_a_id = res_a.json()["id"]

    # User B creates Account B
    res_b = await async_client.post(
        "/api/v1/accounts",
        json={
            "broker_name": "UserB Broker",
            "server_name": "UserB-Server",
            "account_number": "222222",
        },
        headers=user_b["headers"],
    )
    assert res_b.status_code == 201
    account_b_id = res_b.json()["id"]

    # User A lists accounts -> must see Account A, NOT Account B
    list_a = await async_client.get("/api/v1/accounts", headers=user_a["headers"])
    assert list_a.status_code == 200
    ids_a = [acc["id"] for acc in list_a.json()]
    assert account_a_id in ids_a
    assert account_b_id not in ids_a

    # User B lists accounts -> must see Account B, NOT Account A
    list_b = await async_client.get("/api/v1/accounts", headers=user_b["headers"])
    assert list_b.status_code == 200
    ids_b = [acc["id"] for acc in list_b.json()]
    assert account_b_id in ids_b
    assert account_a_id not in ids_b

    # CROSS-USER ACCESS: User B attempts to read Account A directly by ID -> 403 Forbidden
    cross_res = await async_client.get(
        f"/api/v1/accounts/{account_a_id}", headers=user_b["headers"]
    )
    assert cross_res.status_code == 403
    assert cross_res.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_update_account_and_isolation(async_client: AsyncClient):
    """Verifies account update and blocks cross-user modification."""
    user_a = await create_test_user_auth(async_client, "owner_update@example.com")
    user_b = await create_test_user_auth(async_client, "attacker_update@example.com")

    res = await async_client.post(
        "/api/v1/accounts",
        json={
            "broker_name": "Original Broker",
            "server_name": "Original-Server",
            "account_number": "333333",
            "leverage": 100,
        },
        headers=user_a["headers"],
    )
    account_id = res.json()["id"]

    # Legitimate owner updates leverage and adds investor password
    update_payload = {
        "leverage": 200,
        "investor_password": "NewInvestorPassword2026!",
        "broker_name": "Updated Broker LLC",
    }
    res_update = await async_client.put(
        f"/api/v1/accounts/{account_id}",
        json=update_payload,
        headers=user_a["headers"],
    )
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["leverage"] == 200
    assert updated_data["broker_name"] == "Updated Broker LLC"
    assert updated_data["has_investor_password"] is True

    # CROSS-USER UPDATE: User B attempts to update User A's account -> 403 Forbidden
    bad_update = await async_client.put(
        f"/api/v1/accounts/{account_id}",
        json={"leverage": 50},
        headers=user_b["headers"],
    )
    assert bad_update.status_code == 403


@pytest.mark.asyncio
async def test_delete_account_and_safe_retention_policy(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verifies account deletion, cross-user deletion blocking, and data retention safeguards."""
    user_a = await create_test_user_auth(async_client, "del_owner@example.com")
    user_b = await create_test_user_auth(async_client, "del_attacker@example.com")

    # Create Account
    res = await async_client.post(
        "/api/v1/accounts",
        json={
            "broker_name": "Safe Deletion Broker",
            "server_name": "Safe-Server",
            "account_number": "444444",
        },
        headers=user_a["headers"],
    )
    account_id = res.json()["id"]

    # CROSS-USER DELETION: User B tries to delete User A's account -> 403 Forbidden
    bad_del = await async_client.delete(
        f"/api/v1/accounts/{account_id}",
        headers=user_b["headers"],
    )
    assert bad_del.status_code == 403

    from datetime import UTC, datetime

    # Add a simulated Journal Entry to test data retention safeguard
    entry = JournalEntry(
        account_id=uuid.UUID(account_id),
        user_id=user_a["user_id"],
        symbol="EURUSD",
        direction="BUY",
        volume=1.0,
        entry_price=1.0850,
        open_time=datetime.now(UTC),
    )
    db_session.add(entry)
    await db_session.commit()

    # Attempt standard deletion without force -> 409 Conflict
    blocked_del = await async_client.delete(
        f"/api/v1/accounts/{account_id}",
        headers=user_a["headers"],
    )
    assert blocked_del.status_code == 409
    assert "Cannot delete trading account containing" in blocked_del.json()["error"]["message"]
    assert "force=true" in blocked_del.json()["error"]["message"]

    # Call with force=true -> 200 OK
    force_del = await async_client.delete(
        f"/api/v1/accounts/{account_id}?force=true",
        headers=user_a["headers"],
    )
    assert force_del.status_code == 200
    assert force_del.json()["success"] is True

    # Subsequent fetch -> 404 Not Found
    get_res = await async_client.get(
        f"/api/v1/accounts/{account_id}",
        headers=user_a["headers"],
    )
    assert get_res.status_code == 404
