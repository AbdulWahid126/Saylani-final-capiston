"""Automated MT5 Deal Aggregator & Idempotent Synchronization Worker.

Synchronizes historical deals from MetaTrader 5 terminal via read-only IPC,
ingests immutable raw execution deals, aggregates executions into positions,
calculates volume-weighted prices and net financial P&L deterministically,
and guarantees strict multi-tenant isolation and database-level idempotency.
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_resource_ownership
from app.core.config import settings
from app.core.errors import (
    BadRequestError,
    NotFoundError,
    TerminalIntegrationError,
)
from app.core.logging import logger
from app.core.security import decrypt_investor_password
from app.models.account import TradingAccount
from app.models.deal import RawMT5Deal
from app.models.journal import DealJournalMapping, JournalEntry
from app.schemas.mt5 import MT5AccountInfo
from app.schemas.sync import SyncSummaryResponse
from app.services.mt5_connector import MT5Connector


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensures datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def determine_session(dt: datetime) -> str:
    """Classifies UTC trade execution timestamp into market sessions."""
    hour = dt.hour
    if 0 <= hour < 7:
        return "ASIA"
    elif 7 <= hour < 13:
        return "LONDON"
    elif 13 <= hour < 17:
        return "NY_AM"
    elif 17 <= hour < 21:
        return "NY_PM"
    else:
        return "ASIA"


def generate_position_idempotency_hash(account_id: uuid.UUID, broker_position_id: int) -> str:
    """Generates a stable 64-character SHA-256 idempotency hash for a position."""
    raw = f"{account_id}:{broker_position_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SyncWorker:
    """Idempotent MT5 deal synchronizer and position lifecycle aggregator."""

    def __init__(self, connector: MT5Connector | None = None) -> None:
        self.connector = connector

    async def sync_account(
        self,
        account_id: uuid.UUID,
        current_user_id: uuid.UUID,
        db: AsyncSession,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        days: int = 30,
    ) -> SyncSummaryResponse:
        """Synchronizes historical deals for an account and reconciles journal entries.

        Args:
            account_id: Target TradingAccount UUID.
            current_user_id: Authenticated User UUID enforcing multi-tenant boundaries.
            db: Active async database session.
            date_from: Optional explicit start timestamp (UTC).
            date_to: Optional explicit end timestamp (UTC).
            days: Bounded history window in days if date_from is not set (default 30).

        Returns:
            SyncSummaryResponse: Detailed synchronization metrics.
        """
        # 1. Tenant and Account Verification
        account_stmt = select(TradingAccount).where(TradingAccount.id == account_id)
        account = (await db.execute(account_stmt)).scalar_one_or_none()

        if not account:
            raise NotFoundError("TradingAccount", account_id)

        enforce_resource_ownership(account.user_id, current_user_id)

        # 2. Date Bounds Calculation
        now = datetime.now(UTC)
        to_dt = date_to or now
        from_dt = date_from or (to_dt - timedelta(days=days))

        if from_dt > to_dt:
            raise BadRequestError(
                f"Invalid date range: date_from ({from_dt}) cannot be after date_to ({to_dt})."
            )

        logger.info(
            f"Starting deal sync for account {account.account_number} ({account.server_name}) "
            f"over window {from_dt.strftime('%Y-%m-%d')} to {to_dt.strftime('%Y-%m-%d')}"
        )

        account.sync_status = "SYNCING"
        await db.commit()

        # 3. Connection & MT5 Query
        connector = self.connector or MT5Connector()
        should_shutdown = self.connector is None  # Only shutdown if we created the instance

        try:
            if not connector.is_initialized:
                init_kwargs: dict[str, object] = {
                    "path": settings.MT5_TERMINAL_PATH,
                    "timeout": settings.MT5_TIMEOUT_SECONDS * 1000,
                }
                if account.encrypted_investor_pwd:
                    decrypted_pwd = decrypt_investor_password(account.encrypted_investor_pwd)
                    init_kwargs["login"] = int(account.account_number)
                    init_kwargs["password"] = decrypted_pwd
                    init_kwargs["server"] = account.server_name

                connector.initialize(**init_kwargs)

            # Query historical deals from MT5 terminal
            mt5_deals = connector.get_historical_deals(date_from=from_dt, date_to=to_dt)

            # Update live balance and equity if account_info is accessible
            try:
                acc_info = connector.get_account_info()
                if isinstance(acc_info, MT5AccountInfo):
                    account.balance = acc_info.balance
                    account.equity = acc_info.equity
                    account.currency = acc_info.currency
                    account.leverage = acc_info.leverage
                elif acc_info is not None:
                    bal = getattr(acc_info, "balance", None)
                    eq = getattr(acc_info, "equity", None)
                    curr = getattr(acc_info, "currency", None)
                    lev = getattr(acc_info, "leverage", None)
                    if isinstance(bal, int | float):
                        account.balance = float(bal)
                    if isinstance(eq, int | float):
                        account.equity = float(eq)
                    if isinstance(curr, str):
                        account.currency = curr
                    if isinstance(lev, int):
                        account.leverage = lev
            except Exception as e:
                logger.debug(f"Could not refresh live account metrics during sync: {e}")

        except Exception as exc:
            account.sync_status = "ERROR"
            await db.commit()
            logger.error(f"MT5 terminal communication failure during sync: {exc}")
            raise TerminalIntegrationError(
                f"Terminal synchronization failed: {exc}",
                details={"account_id": str(account.id)},
            ) from exc
        finally:
            if should_shutdown:
                connector.shutdown()

        # 4. Ingest Raw Execution Deals (Deduplication via DB tickets)
        existing_tickets_stmt = select(RawMT5Deal.deal_ticket).where(
            RawMT5Deal.account_id == account.id
        )
        existing_tickets = set((await db.execute(existing_tickets_stmt)).scalars().all())

        new_deals_saved = 0
        affected_positions: set[int] = set()

        for d in mt5_deals:
            if d.ticket not in existing_tickets:
                deal_type_str = "BUY" if d.type == 0 else ("SELL" if d.type == 1 else "BALANCE")
                entry_type_str = (
                    "IN"
                    if d.entry == 0
                    else ("OUT" if d.entry == 1 else ("INOUT" if d.entry == 2 else "OUT_BY"))
                )

                raw_deal = RawMT5Deal(
                    account_id=account.id,
                    deal_ticket=d.ticket,
                    order_ticket=d.order if d.order else None,
                    position_ticket=d.position_id,
                    symbol=d.symbol,
                    deal_type=deal_type_str,
                    entry_type=entry_type_str,
                    volume=d.volume,
                    price=d.price,
                    profit=d.profit,
                    commission=d.commission,
                    swap=d.swap,
                    fee=d.fee,
                    deal_time=ensure_utc(d.time),
                )
                db.add(raw_deal)
                existing_tickets.add(d.ticket)
                new_deals_saved += 1

            # Only trade executions (BUY/SELL) with valid position ticket are aggregated into positions
            if d.position_id != 0 and d.type in (0, 1):
                affected_positions.add(d.position_id)

        await db.flush()

        # 5. Position Lifecycle Aggregation & Idempotent Journal Upsert
        open_positions_count = 0
        closed_positions_count = 0

        for pos_id in affected_positions:
            # Query all historical raw deals belonging to this position
            pos_deals_stmt = (
                select(RawMT5Deal)
                .where(
                    RawMT5Deal.account_id == account.id,
                    RawMT5Deal.position_ticket == pos_id,
                )
                .order_by(RawMT5Deal.deal_time.asc())
            )
            pos_deals = list((await db.execute(pos_deals_stmt)).scalars().all())

            if not pos_deals:
                continue

            entry_deals = [
                d
                for d in pos_deals
                if d.entry_type == "IN" or (d.entry_type == "INOUT" and d == pos_deals[0])
            ]
            exit_deals = [
                d
                for d in pos_deals
                if d.entry_type in ("OUT", "OUT_BY")
                or (d.entry_type == "INOUT" and d != pos_deals[0])
            ]

            # Volume calculations
            total_entry_vol = round(sum(d.volume for d in entry_deals), 4)
            total_exit_vol = round(sum(d.volume for d in exit_deals), 4)

            # Fallback if position was transferred or opened prior to query window
            if total_entry_vol == 0:
                total_entry_vol = total_exit_vol if total_exit_vol > 0 else pos_deals[0].volume

            # Deterministic Volume-Weighted Prices
            if entry_deals:
                weighted_entry_price = round(
                    sum(d.price * d.volume for d in entry_deals) / total_entry_vol, 5
                )
            else:
                weighted_entry_price = round(pos_deals[0].price, 5)

            if exit_deals and total_exit_vol > 0:
                weighted_exit_price = round(
                    sum(d.price * d.volume for d in exit_deals) / total_exit_vol, 5
                )
            else:
                weighted_exit_price = None

            # Timestamps
            open_time = (
                min(ensure_utc(d.deal_time) for d in entry_deals)
                if entry_deals
                else ensure_utc(pos_deals[0].deal_time)
            )
            volume_diff = total_entry_vol - total_exit_vol

            # Status determination
            if total_exit_vol == 0:
                status = "OPEN"
                close_time = None
                open_positions_count += 1
            elif volume_diff > 1e-5:
                status = "PARTIAL"
                close_time = None
                open_positions_count += 1
            else:
                status = "CLOSED"
                close_time = (
                    max(ensure_utc(d.deal_time) for d in exit_deals)
                    if exit_deals
                    else ensure_utc(pos_deals[-1].deal_time)
                )
                closed_positions_count += 1

            # Deterministic Financial Metrics (Zero LLM involvement)
            gross_profit = round(sum(d.profit for d in pos_deals), 4)
            commission = round(sum(d.commission for d in pos_deals), 4)
            swap = round(sum(d.swap for d in pos_deals), 4)
            fee = round(sum(d.fee for d in pos_deals), 4)
            net_pnl = round(gross_profit + commission + swap + fee, 4)

            symbol = pos_deals[0].symbol
            direction = entry_deals[0].deal_type if entry_deals else pos_deals[0].deal_type
            idemp_hash = generate_position_idempotency_hash(account.id, pos_id)

            # Check if JournalEntry exists for this account and position ticket
            existing_entry_stmt = select(JournalEntry).where(
                JournalEntry.account_id == account.id,
                JournalEntry.broker_position_id == pos_id,
            )
            target_entry = (await db.execute(existing_entry_stmt)).scalar_one_or_none()

            if target_entry:
                # Update computed market metrics preserving all user-authored journal notes
                target_entry.volume = total_entry_vol
                target_entry.entry_price = weighted_entry_price
                target_entry.exit_price = weighted_exit_price
                target_entry.gross_profit = gross_profit
                target_entry.commission = commission
                target_entry.swap = swap
                target_entry.net_pnl = net_pnl
                target_entry.status = status
                target_entry.close_time = close_time
            else:
                target_entry = JournalEntry(
                    account_id=account.id,
                    user_id=account.user_id,
                    broker_position_id=pos_id,
                    symbol=symbol,
                    direction=direction,
                    volume=total_entry_vol,
                    entry_price=weighted_entry_price,
                    exit_price=weighted_exit_price,
                    gross_profit=gross_profit,
                    commission=commission,
                    swap=swap,
                    net_pnl=net_pnl,
                    open_time=open_time,
                    close_time=close_time,
                    status=status,
                    session=determine_session(open_time),
                    idempotency_hash=idemp_hash,
                )
                db.add(target_entry)
                await db.flush()

            # Reconcile Deal-to-Journal mappings
            mapped_deal_ids_stmt = select(DealJournalMapping.raw_deal_id).where(
                DealJournalMapping.journal_entry_id == target_entry.id
            )
            mapped_deal_ids = set((await db.execute(mapped_deal_ids_stmt)).scalars().all())

            for d in pos_deals:
                if d.id not in mapped_deal_ids:
                    db.add(
                        DealJournalMapping(
                            journal_entry_id=target_entry.id,
                            raw_deal_id=d.id,
                        )
                    )
                    mapped_deal_ids.add(d.id)

        # 6. Finalize Account State
        account.sync_status = "IDLE"
        account.last_sync_at = now
        await db.commit()

        logger.info(
            f"Sync completed for account {account.account_number}. "
            f"Retrieved: {len(mt5_deals)}, New Saved: {new_deals_saved}, Positions: {len(affected_positions)}"
        )

        return SyncSummaryResponse(
            account_id=account.id,
            total_deals_retrieved=len(mt5_deals),
            new_deals_saved=new_deals_saved,
            positions_aggregated=len(affected_positions),
            open_positions_count=open_positions_count,
            closed_positions_count=closed_positions_count,
            sync_status="IDLE",
            synced_at=now,
        )
