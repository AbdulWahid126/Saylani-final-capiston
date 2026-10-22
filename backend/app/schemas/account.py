import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradingAccountCreate(BaseModel):
    """Payload schema for registering a new trading account."""

    broker_name: str = Field(..., min_length=1, max_length=100, description="Brokerage firm name")
    server_name: str = Field(..., min_length=1, max_length=100, description="MT5 trade server name")
    account_number: str = Field(
        ..., min_length=1, max_length=50, description="Broker account identifier"
    )
    account_type: Literal["LIVE", "DEMO", "PROP_CHALLENGE", "PROP_FUNDED"] = Field(
        "DEMO", description="Account classification"
    )
    investor_password: str | None = Field(
        None, min_length=1, max_length=128, description="Read-only investor password (optional)"
    )
    initial_balance: float = Field(0.0, ge=0.0, description="Starting account balance")
    currency: str = Field("USD", min_length=1, max_length=10, description="Deposit base currency")
    leverage: int = Field(100, ge=1, le=5000, description="Account leverage ratio")

    @field_validator("broker_name", "server_name", "account_number")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only")
        return s

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        return v.strip().upper()


class TradingAccountUpdate(BaseModel):
    """Payload schema for modifying an existing trading account."""

    broker_name: str | None = Field(None, min_length=1, max_length=100)
    server_name: str | None = Field(None, min_length=1, max_length=100)
    account_type: Literal["LIVE", "DEMO", "PROP_CHALLENGE", "PROP_FUNDED"] | None = None
    investor_password: str | None = Field(None, min_length=1, max_length=128)
    initial_balance: float | None = Field(None, ge=0.0)
    currency: str | None = Field(None, min_length=1, max_length=10)
    leverage: int | None = Field(None, ge=1, le=5000)
    sync_status: Literal["IDLE", "SYNCING", "ERROR", "DISCONNECTED"] | None = None

    @field_validator("broker_name", "server_name")
    @classmethod
    def strip_optional_whitespace(cls, v: str | None) -> str | None:
        if v is not None:
            s = v.strip()
            if not s:
                raise ValueError("Field cannot be empty or whitespace only")
            return s
        return v


class TradingAccountResponse(BaseModel):
    """Sanitized public trading account representation.

    STRICT SECURITY RULE: Passwords, encryption keys, and raw ciphertexts
    are NEVER exposed or serialized in this schema.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    broker_name: str
    server_name: str
    account_number: str
    account_type: str
    has_investor_password: bool = Field(
        False, description="Whether an encrypted investor password is stored"
    )
    balance: float
    equity: float
    initial_balance: float
    currency: str
    leverage: int
    sync_status: str
    last_sync_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, account: object) -> "TradingAccountResponse":
        """Constructs sanitized response with has_investor_password indicator."""
        has_pwd = bool(getattr(account, "encrypted_investor_pwd", None))
        return cls(
            id=account.id,
            user_id=account.user_id,
            broker_name=account.broker_name,
            server_name=account.server_name,
            account_number=account.account_number,
            account_type=account.account_type,
            has_investor_password=has_pwd,
            balance=getattr(account, "balance", 0.0),
            equity=getattr(account, "equity", 0.0),
            initial_balance=getattr(account, "initial_balance", 0.0),
            currency=getattr(account, "currency", "USD"),
            leverage=getattr(account, "leverage", 100),
            sync_status=getattr(account, "sync_status", "DISCONNECTED"),
            last_sync_at=getattr(account, "last_sync_at", None),
            created_at=account.created_at,
            updated_at=account.updated_at,
        )


class TradingAccountDeleteResponse(BaseModel):
    """Confirmation payload returned on successful account removal."""

    success: bool = True
    message: str
    account_id: uuid.UUID
