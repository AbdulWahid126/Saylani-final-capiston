"""Trading Account management endpoints.

Provides authenticated CRUD operations for MT5 live/demo trading accounts,
enforcing strict multi-tenant isolation and AES-256-GCM credential encryption.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_resource_ownership, get_current_user
from app.core.errors import ConflictError, NotFoundError
from app.core.security import encrypt_investor_password
from app.db.session import get_db
from app.models.account import TradingAccount
from app.models.deal import RawMT5Deal
from app.models.journal import JournalEntry
from app.models.user import User
from app.schemas.account import (
    TradingAccountCreate,
    TradingAccountDeleteResponse,
    TradingAccountResponse,
    TradingAccountUpdate,
)
from app.schemas.sync import SyncRequest, SyncSummaryResponse
from app.services.sync_worker import SyncWorker

router = APIRouter(prefix="/accounts", tags=["Trading Accounts"])


@router.post(
    "",
    response_model=TradingAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new trading account",
)
async def create_trading_account(
    payload: TradingAccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradingAccountResponse:
    """Creates a new trading account for the authenticated user.

    Encrypts investor password with AES-256-GCM before storage and enforces
    uniqueness of (user_id, server_name, account_number).
    """
    # Check for duplicate account for this user
    duplicate_stmt = select(TradingAccount).where(
        TradingAccount.user_id == current_user.id,
        func.lower(TradingAccount.server_name) == payload.server_name.lower().strip(),
        TradingAccount.account_number == payload.account_number.strip(),
    )
    existing = (await db.execute(duplicate_stmt)).scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"Trading account '{payload.account_number}' on server '{payload.server_name}' "
            "is already registered for your user profile."
        )

    # Encrypt password if provided
    encrypted_pwd = None
    if payload.investor_password:
        encrypted_pwd = encrypt_investor_password(payload.investor_password)

    new_account = TradingAccount(
        user_id=current_user.id,
        broker_name=payload.broker_name,
        server_name=payload.server_name,
        account_number=payload.account_number,
        account_type=payload.account_type,
        encrypted_investor_pwd=encrypted_pwd,
        balance=payload.initial_balance,
        equity=payload.initial_balance,
        initial_balance=payload.initial_balance,
        currency=payload.currency,
        leverage=payload.leverage,
        sync_status="DISCONNECTED",
    )

    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)

    return TradingAccountResponse.from_model(new_account)


@router.get(
    "",
    response_model=list[TradingAccountResponse],
    summary="List all trading accounts owned by the authenticated user",
)
async def list_trading_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TradingAccountResponse]:
    """Retrieves all trading accounts owned by the authenticated user.

    Strictly enforces tenant isolation: users never see accounts of other users.
    """
    stmt = (
        select(TradingAccount)
        .where(TradingAccount.user_id == current_user.id)
        .order_by(TradingAccount.created_at.desc())
    )
    result = await db.execute(stmt)
    accounts = result.scalars().all()
    return [TradingAccountResponse.from_model(a) for a in accounts]


@router.get(
    "/{account_id}",
    response_model=TradingAccountResponse,
    summary="Get single trading account details",
)
async def get_trading_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradingAccountResponse:
    """Retrieves details of a single trading account.

    Validates that the authenticated user is the legitimate owner.
    """
    stmt = select(TradingAccount).where(TradingAccount.id == account_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise NotFoundError("TradingAccount", account_id)

    enforce_resource_ownership(account.user_id, current_user.id)
    return TradingAccountResponse.from_model(account)


@router.put(
    "/{account_id}",
    response_model=TradingAccountResponse,
    summary="Update trading account settings or credentials",
)
async def update_trading_account(
    account_id: uuid.UUID,
    payload: TradingAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradingAccountResponse:
    """Updates settings, metadata, or encrypted investor credentials for an account."""
    stmt = select(TradingAccount).where(TradingAccount.id == account_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise NotFoundError("TradingAccount", account_id)

    enforce_resource_ownership(account.user_id, current_user.id)

    if payload.broker_name is not None:
        account.broker_name = payload.broker_name
    if payload.server_name is not None:
        account.server_name = payload.server_name
    if payload.account_type is not None:
        account.account_type = payload.account_type
    if payload.currency is not None:
        account.currency = payload.currency.upper().strip()
    if payload.leverage is not None:
        account.leverage = payload.leverage
    if payload.initial_balance is not None:
        account.initial_balance = payload.initial_balance
    if payload.sync_status is not None:
        account.sync_status = payload.sync_status
    if payload.investor_password is not None:
        if payload.investor_password.strip():
            account.encrypted_investor_pwd = encrypt_investor_password(
                payload.investor_password.strip()
            )
        else:
            account.encrypted_investor_pwd = None

    await db.commit()
    await db.refresh(account)

    return TradingAccountResponse.from_model(account)


@router.delete(
    "/{account_id}",
    response_model=TradingAccountDeleteResponse,
    summary="Delete trading account with safe data retention policy",
)
async def delete_trading_account(
    account_id: uuid.UUID,
    force: bool = Query(
        False,
        description="Permanently delete account along with dependent deals and journal entries",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradingAccountDeleteResponse:
    """Deletes a trading account adhering to safe historical retention rules.

    If the account contains historical deals or journal entries, standard deletion
    is blocked unless 'force=true' is explicitly passed.
    """
    stmt = select(TradingAccount).where(TradingAccount.id == account_id)
    account = (await db.execute(stmt)).scalar_one_or_none()

    if not account:
        raise NotFoundError("TradingAccount", account_id)

    enforce_resource_ownership(account.user_id, current_user.id)

    # Check for existing trade records before allowing deletion
    deal_count_stmt = (
        select(func.count()).select_from(RawMT5Deal).where(RawMT5Deal.account_id == account.id)
    )
    deal_count = (await db.execute(deal_count_stmt)).scalar() or 0

    journal_count_stmt = (
        select(func.count()).select_from(JournalEntry).where(JournalEntry.account_id == account.id)
    )
    journal_count = (await db.execute(journal_count_stmt)).scalar() or 0

    if (deal_count > 0 or journal_count > 0) and not force:
        raise ConflictError(
            f"Cannot delete trading account containing {journal_count} journal entries and "
            f"{deal_count} historical deals. Disconnect the account or pass 'force=true' to confirm permanent deletion.",
            details={"journal_count": journal_count, "deal_count": deal_count},
        )

    await db.delete(account)
    await db.commit()

    return TradingAccountDeleteResponse(
        success=True,
        message="Trading account deleted successfully.",
        account_id=account_id,
    )


@router.post(
    "/{account_id}/sync",
    response_model=SyncSummaryResponse,
    summary="Trigger on-demand MT5 historical deal synchronization for an account",
)
async def sync_trading_account(
    account_id: uuid.UUID,
    payload: SyncRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncSummaryResponse:
    """Synchronizes deals from MT5 for the specified account.

    Strictly verifies ownership by current_user.
    Preserves existing journal notes, aggregates position lifecycles, and maintains idempotency.
    """
    sync_req = payload or SyncRequest()
    worker = SyncWorker()
    return await worker.sync_account(
        account_id=account_id,
        current_user_id=current_user.id,
        db=db,
        date_from=sync_req.date_from,
        date_to=sync_req.date_to,
        days=sync_req.days,
    )
