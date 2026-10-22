"""Comprehensive test suite for TASK-004: JWT Authentication & User Isolation."""

import uuid
from datetime import timedelta

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_resource_ownership
from app.core.config import settings
from app.core.errors import AuthenticationError, ForbiddenError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User

# ============================================================================
# 1. Password Hashing & Cryptography Unit Tests
# ============================================================================


def test_password_hashing_and_verification():
    """Verify that bcrypt hashes plaintext securely and validates properly."""
    raw_password = "Tr@derSecurePass2026!"
    hashed = hash_password(raw_password)

    # Must not store or match plaintext
    assert hashed != raw_password
    assert hashed.startswith("$2b$")

    # Positive match
    assert verify_password(raw_password, hashed) is True

    # Negative matches
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_password, "corrupted_hash") is False

    # Unique salts per generation
    hashed_again = hash_password(raw_password)
    assert hashed != hashed_again
    assert verify_password(raw_password, hashed_again) is True


# ============================================================================
# 2. JWT Access Token Creation & Validation Unit Tests
# ============================================================================


def test_jwt_token_creation_and_decoding():
    """Verify standard RFC 7519 JWT access-token generation and claim decoding."""
    user_id = uuid.uuid4()
    token = create_access_token(subject=user_id)

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["exp"] > payload["iat"]


def test_jwt_token_expiration():
    """Verify that expired tokens are strictly rejected with AuthenticationError."""
    user_id = uuid.uuid4()
    # Create an expired token (10 seconds in the past)
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        decode_access_token(expired_token)
    assert "expired" in str(exc_info.value.message).lower()


def test_jwt_invalid_and_tampered_tokens():
    """Verify that forged or malformed tokens fail verification."""
    # Forged token with invalid secret key
    forged_token = jwt.encode(
        {"sub": str(uuid.uuid4()), "exp": 9999999999, "iat": 1000},
        "wrong-forged-secret-key-min-32-chars-long",
        algorithm="HS256",
    )

    with pytest.raises(AuthenticationError):
        decode_access_token(forged_token)

    with pytest.raises(AuthenticationError):
        decode_access_token("completely.invalid.token")


# ============================================================================
# 3. User Registration Endpoints Tests
# ============================================================================


@pytest.mark.asyncio
async def test_user_registration_success(async_client: AsyncClient, db_session: AsyncSession):
    """Test successful user registration creates record and returns sanitized profile."""
    payload = {
        "email": "alex.trader@example.com",
        "password": "StrongPassword123!",
        "display_name": "Alex Trader",
        "base_currency": "USD",
        "timezone": "America/New_York",
    }

    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "alex.trader@example.com"
    assert data["display_name"] == "Alex Trader"
    assert data["base_currency"] == "USD"
    assert data["timezone"] == "America/New_York"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data

    # Verify database record exists with hashed password
    result = await db_session.execute(select(User).where(User.email == "alex.trader@example.com"))
    user_in_db = result.scalar_one_or_none()
    assert user_in_db is not None
    assert user_in_db.password_hash != "StrongPassword123!"
    assert verify_password("StrongPassword123!", user_in_db.password_hash) is True


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(async_client: AsyncClient):
    """Test registration rejects duplicate email addresses with HTTP 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "display_name": "First User",
    }
    first_res = await async_client.post("/api/v1/auth/register", json=payload)
    assert first_res.status_code == 201

    # Attempt to register with same email in different case
    dup_payload = {
        "email": "DUPLICATE@example.com",
        "password": "DifferentPassword123!",
        "display_name": "Second User",
    }
    dup_res = await async_client.post("/api/v1/auth/register", json=dup_payload)
    assert dup_res.status_code == 409
    error_data = dup_res.json()
    assert error_data["error"]["code"] == "CONFLICT"


@pytest.mark.asyncio
async def test_user_registration_validation(async_client: AsyncClient):
    """Test payload validation for short passwords and malformed emails."""
    # Password too short (< 8 chars)
    short_pw_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "valid@example.com", "password": "short"},
    )
    assert short_pw_res.status_code == 422

    # Malformed email
    bad_email_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "ValidPassword123!"},
    )
    assert bad_email_res.status_code == 422


# ============================================================================
# 4. User Login & Token Issuance Endpoints Tests
# ============================================================================


@pytest.mark.asyncio
async def test_user_login_success(async_client: AsyncClient):
    """Test login with valid credentials returns signed JWT access token."""
    reg_payload = {
        "email": "login.user@example.com",
        "password": "ValidPassword123!",
        "display_name": "Login User",
    }
    await async_client.post("/api/v1/auth/register", json=reg_payload)

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "login.user@example.com", "password": "ValidPassword123!"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()

    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    # Token must decode cleanly
    payload = decode_access_token(token_data["access_token"])
    assert "sub" in payload


@pytest.mark.asyncio
async def test_user_login_invalid_credentials(async_client: AsyncClient):
    """Test login rejects bad passwords and non-existent users with HTTP 401."""
    reg_payload = {
        "email": "auth.victim@example.com",
        "password": "CorrectPassword123!",
    }
    await async_client.post("/api/v1/auth/register", json=reg_payload)

    # Wrong password
    bad_pw_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "auth.victim@example.com", "password": "WrongPassword123!"},
    )
    assert bad_pw_res.status_code == 401
    assert bad_pw_res.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    # Non-existent user
    no_user_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "AnyPassword123!"},
    )
    assert no_user_res.status_code == 401
    assert no_user_res.json()["error"]["code"] == "AUTHENTICATION_FAILED"


# ============================================================================
# 5. Protected /me Endpoint & Authentication Dependency Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_current_user_profile(async_client: AsyncClient):
    """Test authenticated user can retrieve their own profile with Bearer token."""
    reg_payload = {
        "email": "me.profile@example.com",
        "password": "SecurePassword123!",
        "display_name": "Profile Owner",
    }
    reg_res = await async_client.post("/api/v1/auth/register", json=reg_payload)
    user_id = reg_res.json()["id"]

    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "me.profile@example.com", "password": "SecurePassword123!"},
    )
    token = login_res.json()["access_token"]

    # Call /me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["id"] == user_id
    assert me_data["email"] == "me.profile@example.com"
    assert me_data["display_name"] == "Profile Owner"


@pytest.mark.asyncio
async def test_protected_route_rejection(async_client: AsyncClient):
    """Test that missing, invalid, or expired tokens reject protected route access."""
    # 1. Missing Authorization header
    missing_res = await async_client.get("/api/v1/auth/me")
    assert missing_res.status_code == 401
    assert missing_res.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    # 2. Malformed / invalid token
    bad_token_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer malformed.token.value"},
    )
    assert bad_token_res.status_code == 401
    assert bad_token_res.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    # 3. Expired token
    expired_token = create_access_token(
        subject=uuid.uuid4(),
        expires_delta=timedelta(seconds=-30),
    )
    expired_res = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_res.status_code == 401
    assert expired_res.json()["error"]["code"] == "AUTHENTICATION_FAILED"


# ============================================================================
# 6. Strict Multi-Tenant Isolation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_multi_tenant_user_isolation(async_client: AsyncClient):
    """Verify that User A cannot access or impersonate User B."""
    # Register User A
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "user.a@example.com", "password": "PasswordUserA123!"},
    )
    res_a = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "user.a@example.com", "password": "PasswordUserA123!"},
    )
    token_a = res_a.json()["access_token"]

    # Register User B
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "user.b@example.com", "password": "PasswordUserB123!"},
    )
    res_b = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "user.b@example.com", "password": "PasswordUserB123!"},
    )
    token_b = res_b.json()["access_token"]

    # User A /me returns User A
    me_a = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert me_a.json()["email"] == "user.a@example.com"

    # User B /me returns User B
    me_b = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert me_b.json()["email"] == "user.b@example.com"

    # Assert identities are distinct
    assert me_a.json()["id"] != me_b.json()["id"]

    # Test ownership enforcement helper
    user_a_obj = User(
        id=uuid.UUID(me_a.json()["id"]),
        email="user.a@example.com",
        password_hash="hash",
    )
    user_b_id = uuid.UUID(me_b.json()["id"])

    # User A accessing User B's resource raises ForbiddenError (403)
    with pytest.raises(ForbiddenError):
        enforce_resource_ownership(resource_user_id=user_b_id, current_user=user_a_obj)

    # User A accessing User A's resource passes
    enforce_resource_ownership(resource_user_id=user_a_obj.id, current_user=user_a_obj)
