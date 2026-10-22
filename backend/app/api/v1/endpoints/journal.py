"""Journal entry, manual trade management, and CSV import endpoints."""

import hashlib
import math
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_resource_ownership, get_current_user
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.session import get_db
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.models.user import User
from app.schemas.journal import (
    CSVImportResponse,
    CSVPreviewResponse,
    JournalEntryCreate,
    JournalEntryResponse,
    JournalEntryUpdate,
    JournalListResponse,
)
from app.services.csv_importer import CSVTradeImporter
from app.services.sync_worker import determine_session

router = APIRouter(prefix="/journal", tags=["Journal & Trade Entry"])


def resolve_entry_source(entry: JournalEntry) -> str:
    """Classifies source origin of a trade journal entry."""
    if entry.idempotency_hash:
        if entry.idempotency_hash.startswith("csv:"):
            return "CSV"
        if entry.idempotency_hash.startswith("man:"):
            return "MANUAL"
    if entry.broker_position_id is not None:
        return "MT5"
    return "MANUAL"


def to_response_schema(entry: JournalEntry) -> JournalEntryResponse:
    """Transforms SQLAlchemy JournalEntry model to validated response schema."""
    data = {
        "id": entry.id,
        "account_id": entry.account_id,
        "user_id": entry.user_id,
        "broker_position_id": entry.broker_position_id,
        "symbol": entry.symbol,
        "direction": entry.direction,
        "volume": entry.volume,
        "entry_price": entry.entry_price,
        "exit_price": entry.exit_price,
        "stop_loss": entry.stop_loss,
        "take_profit": entry.take_profit,
        "gross_profit": entry.gross_profit,
        "commission": entry.commission,
        "swap": entry.swap,
        "net_pnl": entry.net_pnl,
        "risk_amount": entry.risk_amount,
        "risk_percentage": entry.risk_percentage,
        "rr_ratio": entry.rr_ratio,
        "open_time": entry.open_time,
        "close_time": entry.close_time,
        "status": entry.status,
        "session": entry.session,
        "strategy_id": entry.strategy_id,
        "setup_tag": entry.setup_tag,
        "user_notes": entry.user_notes,
        "emotional_state": entry.emotional_state,
        "idempotency_hash": entry.idempotency_hash,
        "source": resolve_entry_source(entry),
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }
    return JournalEntryResponse(**data)


# -----------------------------------------------------------------------------
# 1. Manual Trade Entry Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/entries",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual trade journal entry",
)
async def create_manual_journal_entry(
    entry_in: JournalEntryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    """Creates a new manual trade record scoped to the authenticated user and account."""
    # Verify target account exists and belongs to authenticated user
    account = (
        await db.execute(select(TradingAccount).where(TradingAccount.id == entry_in.account_id))
    ).scalar_one_or_none()
    if not account:
        raise NotFoundError(
            "Trading account not found.", details={"account_id": str(entry_in.account_id)}
        )
    enforce_resource_ownership(account, current_user.id)

    # Deterministic session calculation
    session_tag = entry_in.session or determine_session(entry_in.open_time)

    # Generate unique manual idempotency hash
    unique_seed = f"manual:{account.id}:{uuid.uuid4()}"
    hash_hex = hashlib.sha256(unique_seed.encode("utf-8")).hexdigest()
    idemp_hash = f"man:{hash_hex[:60]}"

    journal_entry = JournalEntry(
        account_id=account.id,
        user_id=current_user.id,
        broker_position_id=None,
        symbol=entry_in.symbol,
        direction=entry_in.direction,
        volume=entry_in.volume,
        entry_price=entry_in.entry_price,
        exit_price=entry_in.exit_price,
        stop_loss=entry_in.stop_loss,
        take_profit=entry_in.take_profit,
        gross_profit=entry_in.gross_profit,
        commission=entry_in.commission,
        swap=entry_in.swap,
        net_pnl=entry_in.net_pnl if entry_in.net_pnl is not None else 0.0,
        risk_amount=entry_in.risk_amount,
        risk_percentage=entry_in.risk_percentage,
        rr_ratio=entry_in.rr_ratio,
        open_time=entry_in.open_time,
        close_time=entry_in.close_time,
        status=entry_in.status,
        session=session_tag,
        strategy_id=entry_in.strategy_id,
        setup_tag=entry_in.setup_tag,
        user_notes=entry_in.user_notes,
        emotional_state=entry_in.emotional_state,
        idempotency_hash=idemp_hash,
    )

    db.add(journal_entry)
    await db.commit()
    await db.refresh(journal_entry)

    return to_response_schema(journal_entry)


@router.get(
    "/entries",
    response_model=JournalListResponse,
    summary="List trade journal entries with multi-tenant filtering",
)
async def list_journal_entries(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    account_id: uuid.UUID | None = Query(None, description="Filter by trading account ID"),
    symbol: str | None = Query(None, description="Filter by asset symbol"),
    direction: str | None = Query(None, description="Filter by BUY or SELL"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by OPEN, CLOSED, or PARTIAL"
    ),
    date_from: datetime | None = Query(None, description="Start date filter (UTC)"),
    date_to: datetime | None = Query(None, description="End date filter (UTC)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
) -> JournalListResponse:
    """Lists journal entries with tenant isolation and optional filtering."""
    base_conditions = [JournalEntry.user_id == current_user.id]

    if account_id:
        # Check account ownership
        acc = (
            await db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
        ).scalar_one_or_none()
        if not acc:
            raise NotFoundError(
                "Trading account not found.", details={"account_id": str(account_id)}
            )
        enforce_resource_ownership(acc, current_user.id)
        base_conditions.append(JournalEntry.account_id == account_id)

    if symbol:
        base_conditions.append(JournalEntry.symbol == symbol.upper().strip())
    if direction:
        base_conditions.append(JournalEntry.direction == direction.upper().strip())
    if status_filter:
        base_conditions.append(JournalEntry.status == status_filter.upper().strip())
    if date_from:
        base_conditions.append(JournalEntry.open_time >= date_from)
    if date_to:
        base_conditions.append(JournalEntry.open_time <= date_to)

    # Count total
    count_stmt = select(func.count(JournalEntry.id)).where(*base_conditions)
    total_count = (await db.execute(count_stmt)).scalar() or 0

    # Paginated select
    offset = (page - 1) * page_size
    select_stmt = (
        select(JournalEntry)
        .where(*base_conditions)
        .order_by(JournalEntry.open_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    entries = (await db.execute(select_stmt)).scalars().all()

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

    return JournalListResponse(
        items=[to_response_schema(e) for e in entries],
        total=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/entries/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Get single trade journal entry",
)
async def get_journal_entry(
    entry_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    """Retrieves a single journal entry verifying multi-tenant ownership."""
    stmt = select(JournalEntry).where(JournalEntry.id == entry_id)
    entry = (await db.execute(stmt)).scalar_one_or_none()

    if not entry:
        raise NotFoundError("Journal entry not found.", details={"entry_id": str(entry_id)})
    enforce_resource_ownership(entry, current_user.id)

    return to_response_schema(entry)


@router.put(
    "/entries/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Update trade journal entry or discretionary annotations",
)
async def update_journal_entry(
    entry_id: uuid.UUID,
    update_in: JournalEntryUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JournalEntryResponse:
    """Updates a trade journal entry.

    For MT5-synced trades: verified execution metrics (prices, volume, symbol,
    direction) are immutable and cannot be tampered with. Only user annotations
    (notes, setup tag, strategy, emotional state) may be modified.
    """
    stmt = select(JournalEntry).where(JournalEntry.id == entry_id)
    entry = (await db.execute(stmt)).scalar_one_or_none()

    if not entry:
        raise NotFoundError("Journal entry not found.", details={"entry_id": str(entry_id)})
    enforce_resource_ownership(entry, current_user.id)

    is_mt5_synced = entry.broker_position_id is not None and not (
        entry.idempotency_hash
        and (
            entry.idempotency_hash.startswith("csv:")
            or entry.idempotency_hash.startswith("manual:")
        )
    )

    # Guardrail: protect MT5 verified market data from manual tampering
    market_fields = ("symbol", "direction", "volume", "entry_price", "exit_price")
    update_dict = update_in.model_dump(exclude_unset=True)

    if is_mt5_synced and any(k in update_dict for k in market_fields):
        raise BadRequestError(
            "Cannot manually modify execution metrics (symbol, direction, volume, prices) for MT5-synchronized trades. "
            "You may only update discretionary annotations (user_notes, setup_tag, emotional_state, strategy_id)."
        )

    # Apply updates
    for field, val in update_dict.items():
        setattr(entry, field, val)

    # Recompute net_pnl if financial fields were modified
    if (
        any(k in update_dict for k in ("gross_profit", "commission", "swap"))
        and "net_pnl" not in update_dict
    ):
        entry.net_pnl = round(entry.gross_profit + entry.commission + entry.swap, 4)

    # Recompute R:R if SL and TP were modified
    if entry.stop_loss and entry.take_profit and not update_in.rr_ratio:
        if entry.direction == "BUY":
            risk = entry.entry_price - entry.stop_loss
            reward = entry.take_profit - entry.entry_price
        else:
            risk = entry.stop_loss - entry.entry_price
            reward = entry.entry_price - entry.take_profit
        if risk > 0 and reward > 0:
            entry.rr_ratio = round(reward / risk, 2)

    await db.commit()
    await db.refresh(entry)

    return to_response_schema(entry)


@router.delete(
    "/entries/{entry_id}",
    summary="Delete a manual or CSV trade journal entry",
)
async def delete_journal_entry(
    entry_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: bool = Query(
        False, description="Explicit confirmation required to delete synced entries"
    ),
) -> dict[str, str]:
    """Deletes a journal entry verifying ownership. Never deletes raw MT5 deals."""
    stmt = select(JournalEntry).where(JournalEntry.id == entry_id)
    entry = (await db.execute(stmt)).scalar_one_or_none()

    if not entry:
        raise NotFoundError("Journal entry not found.", details={"entry_id": str(entry_id)})
    enforce_resource_ownership(entry, current_user.id)

    is_mt5_synced = entry.broker_position_id is not None and not (
        entry.idempotency_hash
        and (
            entry.idempotency_hash.startswith("csv:")
            or entry.idempotency_hash.startswith("manual:")
        )
    )

    if is_mt5_synced and not force:
        raise ConflictError(
            "This trade is linked to verified MT5 broker deals. "
            "Deleting it requires the explicit query parameter 'force=true'. Underlying raw deals will be preserved."
        )

    await db.delete(entry)
    await db.commit()

    return {"message": "Journal entry successfully deleted.", "id": str(entry_id)}


# -----------------------------------------------------------------------------
# 2. CSV Import & Preview Endpoints
# -----------------------------------------------------------------------------


@router.post(
    "/csv/preview",
    response_model=CSVPreviewResponse,
    summary="Preview and validate CSV trade history without importing",
)
async def preview_csv_trades(
    account_id: Annotated[uuid.UUID, Form(description="Target trading account UUID")],
    file: Annotated[UploadFile, File(description="CSV trade report export")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CSVPreviewResponse:
    """Parses and validates a CSV trade report, reporting row-level errors and sample rows."""
    file_bytes = await file.read()
    importer = CSVTradeImporter()
    return await importer.preview_csv(
        file_bytes=file_bytes,
        account_id=account_id,
        current_user_id=current_user.id,
        db=db,
    )


@router.post(
    "/csv/import",
    response_model=CSVImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import CSV trade history with idempotent duplicate prevention",
)
async def import_csv_trades(
    account_id: Annotated[uuid.UUID, Form(description="Target trading account UUID")],
    file: Annotated[UploadFile, File(description="CSV trade report export")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CSVImportResponse:
    """Imports valid CSV trades transactionally into journal_entries."""
    file_bytes = await file.read()
    importer = CSVTradeImporter()
    return await importer.import_csv(
        file_bytes=file_bytes,
        account_id=account_id,
        current_user_id=current_user.id,
        db=db,
    )


# Account-nested routes for client convenience
@router.post(
    "/accounts/{account_id}/csv/preview",
    response_model=CSVPreviewResponse,
    summary="Account-nested preview of CSV trade history",
)
async def account_nested_preview_csv(
    account_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="CSV trade report export")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CSVPreviewResponse:
    file_bytes = await file.read()
    importer = CSVTradeImporter()
    return await importer.preview_csv(
        file_bytes=file_bytes,
        account_id=account_id,
        current_user_id=current_user.id,
        db=db,
    )


@router.post(
    "/accounts/{account_id}/csv",
    response_model=CSVImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Account-nested import of CSV trade history",
)
async def account_nested_import_csv(
    account_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="CSV trade report export")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CSVImportResponse:
    file_bytes = await file.read()
    importer = CSVTradeImporter()
    return await importer.import_csv(
        file_bytes=file_bytes,
        account_id=account_id,
        current_user_id=current_user.id,
        db=db,
    )
