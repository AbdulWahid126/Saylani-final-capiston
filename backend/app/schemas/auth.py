"""Pydantic v2 schemas for authentication, registration, and user profiles."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Payload schema for user registration."""

    email: EmailStr = Field(
        ...,
        description="Valid unique email address for the user account",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Plaintext password (8 to 72 characters)",
    )
    display_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional display name for dashboard greetings",
    )
    base_currency: str = Field(
        default="USD",
        min_length=3,
        max_length=10,
        description="Account primary currency denomination (e.g. USD, EUR, GBP)",
    )
    timezone: str = Field(
        default="UTC",
        min_length=1,
        max_length=50,
        description="Trader local timezone for session classification",
    )


class UserLoginRequest(BaseModel):
    """Payload schema for user credential authentication."""

    email: EmailStr = Field(
        ...,
        description="Registered user account email",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=72,
        description="User password",
    )


class TokenResponse(BaseModel):
    """Standard RFC 6749 OAuth2 bearer token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ...,
        description="Token expiration duration in seconds",
    )


class UserResponse(BaseModel):
    """Sanitized user representation schema safe for public transmission."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None = None
    base_currency: str = "USD"
    timezone: str = "UTC"
    created_at: datetime
    updated_at: datetime
