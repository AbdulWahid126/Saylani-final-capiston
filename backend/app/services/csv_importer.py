"""Deterministic CSV Trade History Importer & Preview Engine.

Parses, canonicalizes, validates, and imports historical trade records from
standard MT5 reports and generic broker CSV exports. Enforces strict file-size
and row-count boundaries, formula-injection sanitization, multi-tenant ownership,
and database-level idempotency without LLM involvement.
"""

import csv
import hashlib
import io
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import enforce_resource_ownership
from app.core.config import settings
from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.models.account import TradingAccount
from app.models.journal import JournalEntry
from app.schemas.journal import (
    CSVImportResponse,
    CSVPreviewResponse,
    CSVRowError,
)
from app.services.sync_worker import determine_session, ensure_utc


def sanitize_formula_injection(value: str) -> str:
    """Neutralizes spreadsheet formula injection vulnerabilities.

    Leading characters (=, +, -, @, tab, cr) can trigger code execution
    in spreadsheet viewers when exported. We prepend an apostrophe if present.
    """
    if not value:
        return value
    stripped = value.strip()
    if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r"):
        # For numeric values with a leading + or -, do not sanitize as formula
        try:
            float(stripped)
            return value
        except ValueError:
            return f"'{value}"
    return value


def parse_flexible_datetime(val: str) -> datetime:
    """Parses various date/time formats common in MT5 and broker exports."""
    val = val.strip()
    if not val:
        raise ValueError("Date string is empty.")

    # Standard ISO formats
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        return ensure_utc(dt)
    except ValueError:
        pass

    # Common MT5 and broker formats
    candidate_formats = [
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y %I:%M %p",
        "%Y-%m-%d",
        "%Y.%m.%d",
        "%d.%m.%Y",
    ]

    for fmt in candidate_formats:
        try:
            dt = datetime.strptime(val, fmt)
            return ensure_utc(dt)
        except ValueError:
            continue

    raise ValueError(
        f"Unrecognized date/time format: '{val}'. Expected YYYY.MM.DD HH:MM:SS or ISO 8601."
    )


class CSVTradeImporter:
    """Safe CSV trade importer and preview engine with strict validations."""

    HEADER_ALIASES: dict[str, list[str]] = {
        "ticket": ["ticket", "position", "deal", "order", "id", "transid"],
        "open_time": ["opentime", "opendate", "time", "date", "open", "opened"],
        "close_time": ["closetime", "closedate", "closed"],
        "symbol": ["symbol", "item", "asset", "instrument", "pair", "security"],
        "direction": ["type", "direction", "action", "cmd", "side"],
        "volume": ["volume", "size", "lots", "shares", "amount", "qty", "quantity"],
        "entry_price": ["openprice", "price", "open", "entryprice", "entry"],
        "exit_price": ["closeprice", "exitprice", "close", "exit"],
        "stop_loss": ["stoploss", "sl", "stop"],
        "take_profit": ["takeprofit", "tp", "target"],
        "gross_profit": ["profit", "grossprofit", "pl", "pnl", "realizedpnl"],
        "commission": ["commission", "comm", "fees", "fee"],
        "swap": ["swap", "rollover", "financing", "interest"],
        "net_pnl": ["netpnl", "netprofit", "net"],
        "user_notes": ["comment", "notes", "usernotes", "memo", "description"],
        "setup_tag": ["strategy", "strategytag", "playbook", "setup", "setuptag"],
    }

    def _decode_content(self, file_bytes: bytes) -> str:
        """Safely decodes raw uploaded bytes, checking size and encoding."""
        if len(file_bytes) > settings.MAX_CSV_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_CSV_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise BadRequestError(
                f"Uploaded CSV exceeds maximum allowed file size of {max_mb} MB.",
                details={
                    "file_size_bytes": len(file_bytes),
                    "max_allowed_bytes": settings.MAX_CSV_UPLOAD_SIZE_BYTES,
                },
            )

        if not file_bytes:
            raise BadRequestError("Uploaded CSV file is completely empty.")

        # Try UTF-8 with BOM first, then UTF-8, then fallback to latin-1
        try:
            return file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                return file_bytes.decode("latin-1")
            except Exception as e:
                raise BadRequestError(
                    f"Unable to decode CSV file: {e}. Please ensure file is valid UTF-8 or ASCII text."
                ) from e

    def _canonicalize_headers(self, raw_headers: list[str]) -> dict[int, str]:
        """Maps column indices to canonical field names, handling duplicate MT5 columns.

        In standard MT5 reports, duplicate headers like 'Time' and 'Price' occur twice:
        the first represents Open Time/Price, and the second represents Close Time/Price.
        """
        mapped: dict[int, str] = {}
        seen_canonical: dict[str, int] = {}

        for idx, raw_h in enumerate(raw_headers):
            clean_h = re.sub(r"[\s_\-\/\&]+", "", raw_h).lower()
            normalized_field = None

            for canon, aliases in self.HEADER_ALIASES.items():
                if clean_h in aliases:
                    normalized_field = canon
                    break

            if normalized_field:
                # Handle second occurrence of Time or Price in MT5 reports
                if normalized_field == "open_time" and "open_time" in seen_canonical:
                    normalized_field = "close_time"
                elif normalized_field == "entry_price" and "entry_price" in seen_canonical:
                    normalized_field = "exit_price"

                mapped[idx] = normalized_field
                seen_canonical[normalized_field] = seen_canonical.get(normalized_field, 0) + 1

        return mapped

    def parse_trades(
        self,
        file_bytes: bytes,
        account_id: uuid.UUID,
    ) -> tuple[list[dict[str, Any]], list[CSVRowError], int]:
        """Parses and validates CSV trade records without database side effects.

        Returns:
            tuple: (valid_parsed_trades, errors, total_raw_rows)
        """
        content = self._decode_content(file_bytes)
        reader = csv.reader(io.StringIO(content))

        raw_rows: list[list[str]] = []
        for row in reader:
            # Skip empty lines
            if any(cell.strip() for cell in row):
                raw_rows.append(row)

        if not raw_rows:
            raise BadRequestError("CSV file contains no readable data rows.")

        if len(raw_rows) - 1 > settings.MAX_CSV_IMPORT_ROWS:
            raise BadRequestError(
                f"CSV contains {len(raw_rows) - 1} data rows, exceeding maximum limit of {settings.MAX_CSV_IMPORT_ROWS} rows."
            )

        header_row = raw_rows[0]
        header_map = self._canonicalize_headers(header_row)

        # Mandatory fields check
        required_fields = {"symbol", "direction", "volume", "entry_price", "open_time"}
        mapped_values = set(header_map.values())
        missing_fields = required_fields - mapped_values

        if missing_fields:
            raise BadRequestError(
                f"CSV is missing required columns: {sorted(missing_fields)}. "
                f"Detected columns: {[h.strip() for h in header_row if h.strip()]}."
            )

        valid_trades: list[dict[str, Any]] = []
        errors: list[CSVRowError] = []
        seen_hashes: set[str] = set()

        for row_idx, row in enumerate(raw_rows[1:], start=2):
            row_dict: dict[str, str] = {}
            for col_idx, cell in enumerate(row):
                if col_idx in header_map:
                    row_dict[header_map[col_idx]] = sanitize_formula_injection(cell.strip())

            # 1. Symbol validation
            raw_sym = row_dict.get("symbol", "")
            if not raw_sym:
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="symbol",
                        message="Symbol is required and cannot be empty.",
                    )
                )
                continue
            symbol = raw_sym.upper().strip()
            if not re.match(r"^[A-Z0-9_\.\-\/]{1,30}$", symbol):
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="symbol",
                        message=f"Invalid symbol format '{raw_sym}'. Must be 1-30 alphanumeric characters.",
                        raw_value=raw_sym,
                    )
                )
                continue

            # 2. Direction validation
            raw_dir = row_dict.get("direction", "").upper().strip()
            if raw_dir in ("BUY", "LONG", "0"):
                direction = "BUY"
            elif raw_dir in ("SELL", "SHORT", "1"):
                direction = "SELL"
            else:
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="direction",
                        message=f"Invalid trade direction '{raw_dir}'. Expected 'BUY' or 'SELL'.",
                        raw_value=raw_dir,
                    )
                )
                continue

            # 3. Volume validation
            raw_vol = row_dict.get("volume", "")
            try:
                volume = round(float(raw_vol), 4)
                if volume <= 0:
                    errors.append(
                        CSVRowError(
                            row=row_idx,
                            field="volume",
                            message=f"Volume must be strictly greater than 0, got {volume}.",
                            raw_value=raw_vol,
                        )
                    )
                    continue
            except (ValueError, TypeError):
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="volume",
                        message=f"Invalid numeric volume '{raw_vol}'.",
                        raw_value=raw_vol,
                    )
                )
                continue

            # 4. Entry Price validation
            raw_entry = row_dict.get("entry_price", "")
            try:
                entry_price = round(float(raw_entry), 5)
                if entry_price <= 0:
                    errors.append(
                        CSVRowError(
                            row=row_idx,
                            field="entry_price",
                            message=f"Entry price must be strictly greater than 0, got {entry_price}.",
                            raw_value=raw_entry,
                        )
                    )
                    continue
            except (ValueError, TypeError):
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="entry_price",
                        message=f"Invalid numeric entry price '{raw_entry}'.",
                        raw_value=raw_entry,
                    )
                )
                continue

            # 5. Open Time validation
            raw_open_time = row_dict.get("open_time", "")
            try:
                open_time = parse_flexible_datetime(raw_open_time)
            except Exception as e:
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="open_time",
                        message=f"Invalid open timestamp: {e}",
                        raw_value=raw_open_time,
                    )
                )
                continue

            # 6. Exit Price and Close Time (Optional for open trades)
            exit_price: float | None = None
            raw_exit = row_dict.get("exit_price")
            if raw_exit and raw_exit not in ("0", "0.0", "0.00", "-"):
                try:
                    exit_price = round(float(raw_exit), 5)
                    if exit_price <= 0:
                        exit_price = None
                except ValueError:
                    errors.append(
                        CSVRowError(
                            row=row_idx,
                            field="exit_price",
                            message=f"Invalid numeric exit price '{raw_exit}'.",
                            raw_value=raw_exit,
                        )
                    )
                    continue

            close_time: datetime | None = None
            raw_close_time = row_dict.get("close_time")
            if raw_close_time and raw_close_time not in ("0", "0.0", "-"):
                try:
                    close_time = parse_flexible_datetime(raw_close_time)
                    if close_time < open_time:
                        errors.append(
                            CSVRowError(
                                row=row_idx,
                                field="close_time",
                                message=f"Close time ({close_time}) cannot be earlier than open time ({open_time}).",
                                raw_value=raw_close_time,
                            )
                        )
                        continue
                except Exception as e:
                    errors.append(
                        CSVRowError(
                            row=row_idx,
                            field="close_time",
                            message=f"Invalid close timestamp: {e}",
                            raw_value=raw_close_time,
                        )
                    )
                    continue

            # 7. Financial Metrics
            gross_profit = 0.0
            raw_profit = row_dict.get("gross_profit")
            if raw_profit:
                try:
                    gross_profit = round(float(raw_profit), 4)
                except ValueError:
                    gross_profit = 0.0

            commission = 0.0
            raw_comm = row_dict.get("commission")
            if raw_comm:
                try:
                    commission = round(float(raw_comm), 4)
                except ValueError:
                    commission = 0.0

            swap = 0.0
            raw_swap = row_dict.get("swap")
            if raw_swap:
                try:
                    swap = round(float(raw_swap), 4)
                except ValueError:
                    swap = 0.0

            raw_net = row_dict.get("net_pnl")
            if raw_net:
                try:
                    net_pnl = round(float(raw_net), 4)
                except ValueError:
                    net_pnl = round(gross_profit + commission + swap, 4)
            else:
                net_pnl = round(gross_profit + commission + swap, 4)

            # 8. Stop Loss & Take Profit
            stop_loss: float | None = None
            raw_sl = row_dict.get("stop_loss")
            if raw_sl and raw_sl not in ("0", "0.0", "-"):
                try:
                    stop_loss = round(float(raw_sl), 5)
                    if stop_loss <= 0:
                        stop_loss = None
                except ValueError:
                    stop_loss = None

            take_profit: float | None = None
            raw_tp = row_dict.get("take_profit")
            if raw_tp and raw_tp not in ("0", "0.0", "-"):
                try:
                    take_profit = round(float(raw_tp), 5)
                    if take_profit <= 0:
                        take_profit = None
                except ValueError:
                    take_profit = None

            # Calculate R:R Ratio deterministically
            rr_ratio: float | None = None
            if stop_loss and take_profit:
                if direction == "BUY":
                    risk = entry_price - stop_loss
                    reward = take_profit - entry_price
                else:
                    risk = stop_loss - entry_price
                    reward = entry_price - take_profit

                if risk > 0 and reward > 0:
                    rr_ratio = round(reward / risk, 2)

            # Status determination
            status = "CLOSED" if (close_time or exit_price is not None) else "OPEN"

            # Optional broker position/ticket
            broker_position_id: int | None = None
            raw_ticket = row_dict.get("ticket")
            if raw_ticket:
                try:
                    broker_position_id = int(raw_ticket)
                except ValueError:
                    broker_position_id = None

            # Generate stable idempotency hash
            if broker_position_id:
                raw_hash_seed = f"csv:{account_id}:{broker_position_id}"
            else:
                raw_hash_seed = f"csv:{account_id}:{symbol}:{open_time.isoformat()}:{direction}:{volume}:{entry_price}"
            hash_hex = hashlib.sha256(raw_hash_seed.encode("utf-8")).hexdigest()
            idempotency_hash = f"csv:{hash_hex[:60]}"

            # Skip duplicate row within the uploaded file itself
            if idempotency_hash in seen_hashes:
                errors.append(
                    CSVRowError(
                        row=row_idx,
                        field="ticket",
                        message=f"Duplicate trade detected in CSV file (row {row_idx} matches earlier entry).",
                        raw_value=raw_ticket or symbol,
                    )
                )
                continue

            seen_hashes.add(idempotency_hash)

            valid_trades.append(
                {
                    "account_id": account_id,
                    "broker_position_id": broker_position_id,
                    "symbol": symbol,
                    "direction": direction,
                    "volume": volume,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "gross_profit": gross_profit,
                    "commission": commission,
                    "swap": swap,
                    "net_pnl": net_pnl,
                    "open_time": open_time,
                    "close_time": close_time,
                    "status": status,
                    "session": determine_session(open_time),
                    "rr_ratio": rr_ratio,
                    "user_notes": row_dict.get("user_notes"),
                    "setup_tag": row_dict.get("setup_tag"),
                    "idempotency_hash": idempotency_hash,
                }
            )

        return valid_trades, errors, len(raw_rows) - 1

    async def preview_csv(
        self,
        file_bytes: bytes,
        account_id: uuid.UUID,
        current_user_id: uuid.UUID,
        db: AsyncSession,
    ) -> CSVPreviewResponse:
        """Parses and validates CSV trades, returning summary without committing to database."""
        # Multi-tenant resource ownership check
        account = (
            await db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
        ).scalar_one_or_none()
        if not account:
            raise NotFoundError(
                "Trading account not found.", details={"account_id": str(account_id)}
            )
        enforce_resource_ownership(account, current_user_id)

        valid_trades, errors, total_rows = self.parse_trades(file_bytes, account_id)

        sample_trades = [
            {
                "symbol": t["symbol"],
                "direction": t["direction"],
                "volume": t["volume"],
                "entry_price": t["entry_price"],
                "exit_price": t["exit_price"],
                "open_time": t["open_time"].isoformat(),
                "status": t["status"],
                "net_pnl": t["net_pnl"],
            }
            for t in valid_trades[:5]
        ]

        return CSVPreviewResponse(
            total_rows=total_rows,
            valid_rows_count=len(valid_trades),
            error_rows_count=len(errors),
            sample_valid_rows=sample_trades,
            errors=errors,
        )

    async def import_csv(
        self,
        file_bytes: bytes,
        account_id: uuid.UUID,
        current_user_id: uuid.UUID,
        db: AsyncSession,
    ) -> CSVImportResponse:
        """Transactionally commits valid CSV trades into journal_entries.

        Strictly enforces database idempotency: existing trades matching
        idempotency_hash are skipped to prevent duplicate records on retries.
        """
        # Multi-tenant resource ownership check
        account = (
            await db.execute(select(TradingAccount).where(TradingAccount.id == account_id))
        ).scalar_one_or_none()
        if not account:
            raise NotFoundError(
                "Trading account not found.", details={"account_id": str(account_id)}
            )
        enforce_resource_ownership(account, current_user_id)

        valid_trades, errors, total_rows = self.parse_trades(file_bytes, account_id)

        if not valid_trades and errors:
            raise BadRequestError(
                f"CSV import failed: all {len(errors)} data rows contain validation errors.",
                details={"errors_count": len(errors)},
            )

        # Query all existing idempotency hashes for this account to prevent duplicates
        existing_hashes_stmt = select(JournalEntry.idempotency_hash).where(
            JournalEntry.account_id == account_id,
            JournalEntry.idempotency_hash.is_not(None),
        )
        existing_hashes = set((await db.execute(existing_hashes_stmt)).scalars().all())

        imported_count = 0
        duplicates_skipped = 0

        try:
            for trade_data in valid_trades:
                h = trade_data["idempotency_hash"]
                if h in existing_hashes:
                    duplicates_skipped += 1
                    continue

                entry = JournalEntry(
                    account_id=account.id,
                    user_id=current_user_id,
                    broker_position_id=trade_data["broker_position_id"],
                    symbol=trade_data["symbol"],
                    direction=trade_data["direction"],
                    volume=trade_data["volume"],
                    entry_price=trade_data["entry_price"],
                    exit_price=trade_data["exit_price"],
                    stop_loss=trade_data["stop_loss"],
                    take_profit=trade_data["take_profit"],
                    gross_profit=trade_data["gross_profit"],
                    commission=trade_data["commission"],
                    swap=trade_data["swap"],
                    net_pnl=trade_data["net_pnl"],
                    rr_ratio=trade_data["rr_ratio"],
                    open_time=trade_data["open_time"],
                    close_time=trade_data["close_time"],
                    status=trade_data["status"],
                    session=trade_data["session"],
                    user_notes=trade_data["user_notes"],
                    setup_tag=trade_data["setup_tag"],
                    idempotency_hash=h,
                )
                db.add(entry)
                existing_hashes.add(h)
                imported_count += 1

            await db.commit()
            logger.info(
                f"CSV trade import completed for account {account.account_number}. "
                f"Imported: {imported_count}, Skipped Duplicates: {duplicates_skipped}, Errors: {len(errors)}"
            )

            return CSVImportResponse(
                account_id=account.id,
                total_rows=total_rows,
                imported_count=imported_count,
                duplicates_skipped=duplicates_skipped,
                error_rows_count=len(errors),
                errors=errors,
            )

        except Exception as exc:
            await db.rollback()
            logger.error(f"Transaction failed during CSV trade import: {exc}")
            raise
