"""Security and cryptographic operations module for AI Trading Copilot.

Provides password hashing via bcrypt and RFC 7519 JWT access-token management
without leaking secrets into logs or exception traces.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AuthenticationError

BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Securely hash a plaintext password using bcrypt with work factor 12."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hashed password in constant time."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a signed RFC 7519 JWT access token with standard claims."""
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Validate and decode a signed JWT access token.

    Raises AuthenticationError if the token is invalid, expired, or malformed.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid authentication token") from exc


# -----------------------------------------------------------------------------
# AES-256-GCM Credential Encryption (Law of Secret Hygiene)
# -----------------------------------------------------------------------------
def validate_encryption_key(key: str | bytes | None = None) -> bytes:
    """Validates and derives an exact 32-byte AES-256 key from config or explicit input.

    Raises ValueError if key is invalid, missing, or the default dev key in production.
    """
    raw_key = key if key is not None else settings.ENCRYPTION_KEY
    if not raw_key:
        raise ValueError("Encryption key cannot be empty.")

    # Guard against default development key in production environment
    if settings.is_production and isinstance(raw_key, str):
        insecure_keys = {
            "ZGV2XzMyX2J5dGVfYWVzX2djbV9zZWNyZXRfa2V5MTI=",
            "development-32byte-aes-gcm-key-change-in-prod=",
            "generate-a-32-byte-base64-key-for-aes-256-gcm=",
        }
        if raw_key in insecure_keys or "dev" in raw_key.lower():
            raise ValueError(
                "Default development ENCRYPTION_KEY is strictly forbidden in production environments."
            )

    if isinstance(raw_key, bytes):
        if len(raw_key) != 32:
            raise ValueError(
                f"Invalid encryption key configuration: expected 32 bytes, got {len(raw_key)} bytes."
            )
        return raw_key

    if isinstance(raw_key, str):
        # 1. Try 64-char hex
        if len(raw_key) == 64:
            try:
                hex_bytes = bytes.fromhex(raw_key)
                if len(hex_bytes) == 32:
                    return hex_bytes
            except ValueError:
                pass

        # 2. Try Base64 decoding
        try:
            import base64

            b64_bytes = base64.b64decode(raw_key, validate=True)
            if len(b64_bytes) == 32:
                return b64_bytes
        except Exception:
            pass

        # 3. Try raw 32-byte string
        raw_bytes = raw_key.encode("utf-8")
        if len(raw_bytes) == 32:
            return raw_bytes

        raise ValueError(
            f"Invalid encryption key configuration: expected 32 bytes (or 32-byte base64/hex), got {len(raw_key)} characters."
        )

    raise ValueError("Invalid encryption key type. Expected str or bytes.")


def encrypt_investor_password(plain_password: str, key: str | bytes | None = None) -> str:
    """Encrypts plaintext investor password using AES-256-GCM authenticated encryption.

    Generates a cryptographically secure 12-byte nonce (os.urandom), encrypts with GCM,
    and returns a base64 string combining nonce + ciphertext + authentication tag.
    """
    if not plain_password:
        raise ValueError("Password to encrypt cannot be empty.")

    import base64
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key_bytes = validate_encryption_key(key)
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)  # Standard 96-bit GCM nonce
    ciphertext = aesgcm.encrypt(nonce, plain_password.encode("utf-8"), None)
    payload = nonce + ciphertext
    return base64.b64encode(payload).decode("utf-8")


def decrypt_investor_password(encrypted_payload: str, key: str | bytes | None = None) -> str:
    """Decrypts AES-256-GCM encrypted payload and verifies authenticity.

    Extracts the 12-byte nonce and validates the authentication tag.
    Raises ValueError on tampering, wrong key, or malformed payload.
    """
    if not encrypted_payload:
        raise ValueError("Encrypted payload cannot be empty.")

    import base64

    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key_bytes = validate_encryption_key(key)
    aesgcm = AESGCM(key_bytes)

    try:
        raw_payload = base64.b64decode(encrypted_payload.encode("utf-8"), validate=True)
    except Exception as exc:
        raise ValueError("Malformed encrypted payload (invalid base64 encoding).") from exc

    # Minimum payload: 12-byte nonce + 16-byte GCM authentication tag = 28 bytes
    if len(raw_payload) < 28:
        raise ValueError("Invalid encrypted payload size (missing nonce or authentication tag).")

    nonce = raw_payload[:12]
    ciphertext_and_tag = raw_payload[12:]

    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
        return decrypted_bytes.decode("utf-8")
    except InvalidTag as exc:
        raise ValueError(
            "Decryption failed: authentication tag verification failed (tampered ciphertext or wrong key)."
        ) from exc
