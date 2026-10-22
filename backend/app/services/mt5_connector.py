"""MetaTrader 5 Windows Terminal IPC Connector (Read-Only).

Integrates with the official MetaTrader5 package using low-latency local IPC.
Strictly read-only: Order execution, modification, and cancellation are forbidden
by the Law of Read-Only Safety.
"""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

from app.core.config import settings
from app.core.errors import (
    MT5AccountError,
    MT5Error,
    MT5InitializationError,
    MT5QueryError,
)
from app.core.logging import logger
from app.schemas.mt5 import (
    MT5AccountInfo,
    MT5ConnectionDiagnostics,
    MT5DealInfo,
    MT5PositionInfo,
    MT5TerminalStatus,
)


class MT5Connector:
    """Read-only MetaTrader 5 Terminal IPC service.

    Guarantees strict compliance with the Law of Read-Only Safety:
    - Never invokes trading APIs (order_send, order_check, position close).
    - Enforces sanitized credential handling (never logs or prints passwords).
    - Safely releases terminal IPC resources via shutdown() or context managers.
    """

    def __init__(
        self,
        terminal_path: str | None = None,
        timeout_seconds: int | None = None,
        mt5_client: Any = None,
    ) -> None:
        self.terminal_path = terminal_path or settings.MT5_TERMINAL_PATH
        self.timeout_seconds = timeout_seconds or settings.MT5_TIMEOUT_SECONDS
        self._is_initialized = False

        if mt5_client is not None:
            self._mt5 = mt5_client
        else:
            try:
                import MetaTrader5 as mt5

                self._mt5 = mt5
            except ImportError:
                self._mt5 = None

    @property
    def is_initialized(self) -> bool:
        """Returns True if the connector is currently attached to an MT5 terminal."""
        return self._is_initialized

    def _ensure_client(self) -> Any:
        """Ensures the MetaTrader5 client module is available."""
        if self._mt5 is None:
            raise MT5InitializationError(
                "The official MetaTrader5 package is not available. "
                "Ensure it is installed on a 64-bit Windows environment.",
                details={"platform": sys.platform},
            )
        return self._mt5

    def _ensure_initialized(self) -> None:
        """Validates that initialize() has completed successfully before querying."""
        if not self._is_initialized:
            raise MT5InitializationError(
                "MT5 connector is not initialized. Call initialize() before issuing queries."
            )

    def initialize(
        self,
        path: str | None = None,
        login: int | None = None,
        password: str | None = None,
        server: str | None = None,
        timeout: int | None = None,
        portable: bool = False,
    ) -> bool:
        """Initializes connection to the MT5 terminal via Windows IPC.

        Args:
            path: Path to terminal64.exe (defaults to configured path).
            login: Optional account login number.
            password: Optional account password (investor or master; investor preferred).
            server: Optional broker trade server.
            timeout: IPC connection timeout in milliseconds.
            portable: Whether to launch terminal in portable mode.

        Returns:
            bool: True if connection succeeded.

        Raises:
            MT5InitializationError: If terminal binary is missing or initialization fails.
        """
        mt5 = self._ensure_client()
        exec_path = self.terminal_path if path is None else path
        timeout_ms = timeout or (self.timeout_seconds * 1000)

        init_kwargs: dict[str, Any] = {
            "timeout": timeout_ms,
            "portable": portable,
        }

        # Check terminal path existence if an explicit path is provided
        if exec_path:
            resolved_path = (
                str(Path(exec_path).resolve()) if not os.path.isabs(exec_path) else exec_path
            )
            if not os.path.exists(resolved_path):
                raise MT5InitializationError(
                    f"MT5 terminal executable not found at specified path: '{resolved_path}'",
                    details={"path": resolved_path},
                )
            init_kwargs["path"] = resolved_path
        if login is not None:
            init_kwargs["login"] = int(login)
        if password is not None:
            init_kwargs["password"] = password
        if server is not None:
            init_kwargs["server"] = str(server)

        # Masked logging to preserve secret hygiene
        masked_login_str = f"login={str(login)[:3]}***" if login else "default_profile"
        logger.info(
            f"Initializing MT5 connection via IPC (target: {exec_path}, {masked_login_str})"
        )

        try:
            result = mt5.initialize(**init_kwargs)
        except Exception as exc:
            logger.error(f"MT5 initialize threw unhandled exception: {exc}")
            raise MT5InitializationError(
                f"MT5 initialization failed with exception: {exc}",
                details={"exception": str(exc)},
            ) from exc

        if not result:
            err_code, err_desc = mt5.last_error()
            logger.warning(f"MT5 initialize returned False. Code: {err_code}, Error: {err_desc}")
            self._is_initialized = False
            raise MT5InitializationError(
                f"MT5 initialization failed: {err_desc} (code {err_code})",
                details={"error_code": err_code, "error_description": err_desc, "path": exec_path},
            )

        self._is_initialized = True
        logger.info("MT5 IPC connection established successfully.")
        return True

    def get_terminal_status(self) -> MT5TerminalStatus:
        """Retrieves terminal runtime metadata and network connection status.

        Returns:
            MT5TerminalStatus: Validated terminal status schema.
        """
        self._ensure_initialized()
        mt5 = self._ensure_client()

        info = mt5.terminal_info()
        if info is None:
            err_code, err_desc = mt5.last_error()
            raise MT5QueryError(
                f"Failed to retrieve MT5 terminal info: {err_desc} (code {err_code})",
                details={"error_code": err_code},
            )

        return MT5TerminalStatus(
            connected=bool(getattr(info, "connected", False)),
            trade_allowed=bool(getattr(info, "trade_allowed", False)),
            build=int(getattr(info, "build", 0)),
            name=str(getattr(info, "name", "MetaTrader 5")),
            path=str(getattr(info, "path", self.terminal_path)),
            ping_last=int(getattr(info, "ping_last", 0)),
            company=str(getattr(info, "company", "")),
            community_account=bool(getattr(info, "community_account", False)),
        )

    def get_account_info(self) -> MT5AccountInfo:
        """Retrieves read-only account balance, equity, leverage, and server details.

        Returns:
            MT5AccountInfo: Validated account info schema.

        Raises:
            MT5AccountError: If account information cannot be queried or terminal is unauthorized.
        """
        self._ensure_initialized()
        mt5 = self._ensure_client()

        account = mt5.account_info()
        if account is None:
            err_code, err_desc = mt5.last_error()
            raise MT5AccountError(
                f"Failed to retrieve MT5 account info: {err_desc} (code {err_code})",
                details={"error_code": err_code, "error_description": err_desc},
            )

        return MT5AccountInfo(
            login=int(getattr(account, "login", 0)),
            server=str(getattr(account, "server", "")),
            currency=str(getattr(account, "currency", "USD")),
            balance=float(getattr(account, "balance", 0.0)),
            equity=float(getattr(account, "equity", 0.0)),
            profit=float(getattr(account, "profit", 0.0)),
            margin=float(getattr(account, "margin", 0.0)),
            margin_free=float(getattr(account, "margin_free", 0.0)),
            margin_level=getattr(account, "margin_level", None),
            leverage=int(getattr(account, "leverage", 1)),
            trade_mode=int(getattr(account, "trade_mode", 0)),
            company=str(getattr(account, "company", "")),
            name=str(getattr(account, "name", "")),
            trade_allowed=bool(getattr(account, "trade_allowed", False)),
        )

    def get_historical_deals(
        self,
        date_from: datetime,
        date_to: datetime,
        position_id: int | None = None,
        ticket: int | None = None,
    ) -> list[MT5DealInfo]:
        """Queries historical execution deals over an explicit bounded date range.

        Args:
            date_from: Start timestamp.
            date_to: End timestamp.
            position_id: Optional filter for deals tied to a specific position ticket.
            ticket: Optional filter for a specific deal ticket.

        Returns:
            list[MT5DealInfo]: Array of typed, validated historical deals.
        """
        self._ensure_initialized()
        mt5 = self._ensure_client()

        if date_from > date_to:
            raise MT5QueryError(
                f"Invalid date range: date_from ({date_from}) cannot be after date_to ({date_to})"
            )

        if ticket is not None:
            deals_raw = mt5.history_deals_get(ticket=ticket)
        elif position_id is not None:
            deals_raw = mt5.history_deals_get(position=position_id)
        else:
            deals_raw = mt5.history_deals_get(date_from, date_to)

        if deals_raw is None:
            err_code, err_desc = mt5.last_error()
            # MT5 may return None with error code 1 (RES_S_OK) or 0 when no deals match
            if err_code not in (0, 1):
                raise MT5QueryError(
                    f"Failed to query historical deals: {err_desc} (code {err_code})",
                    details={"error_code": err_code, "error_description": err_desc},
                )
            deals_raw = ()

        results: list[MT5DealInfo] = []
        for d in deals_raw:
            ts = getattr(d, "time", 0)
            deal_time = datetime.fromtimestamp(ts, tz=UTC) if isinstance(ts, int | float) else ts

            results.append(
                MT5DealInfo(
                    ticket=int(getattr(d, "ticket", 0)),
                    order=int(getattr(d, "order", 0)),
                    time=deal_time,
                    time_msc=int(getattr(d, "time_msc", 0)),
                    type=int(getattr(d, "type", 0)),
                    entry=int(getattr(d, "entry", 0)),
                    magic=int(getattr(d, "magic", 0)),
                    position_id=int(getattr(d, "position_id", 0)),
                    reason=int(getattr(d, "reason", 0)),
                    volume=float(getattr(d, "volume", 0.0)),
                    price=float(getattr(d, "price", 0.0)),
                    commission=float(getattr(d, "commission", 0.0)),
                    swap=float(getattr(d, "swap", 0.0)),
                    profit=float(getattr(d, "profit", 0.0)),
                    fee=float(getattr(d, "fee", 0.0)),
                    symbol=str(getattr(d, "symbol", "")),
                    comment=str(getattr(d, "comment", "")),
                    external_id=str(getattr(d, "external_id", "")),
                )
            )

        return results

    def get_open_positions(
        self,
        symbol: str | None = None,
        ticket: int | None = None,
    ) -> list[MT5PositionInfo]:
        """Queries currently active open market positions for diagnostic inspection.

        STRICTLY READ-ONLY: Never modifies or closes open positions.
        """
        self._ensure_initialized()
        mt5 = self._ensure_client()

        if ticket is not None:
            positions_raw = mt5.positions_get(ticket=ticket)
        elif symbol is not None:
            positions_raw = mt5.positions_get(symbol=symbol)
        else:
            positions_raw = mt5.positions_get()

        if positions_raw is None:
            err_code, err_desc = mt5.last_error()
            if err_code not in (0, 1):
                raise MT5QueryError(
                    f"Failed to query open positions: {err_desc} (code {err_code})",
                    details={"error_code": err_code, "error_description": err_desc},
                )
            positions_raw = ()

        results: list[MT5PositionInfo] = []
        for p in positions_raw:
            ts = getattr(p, "time", 0)
            pos_time = datetime.fromtimestamp(ts, tz=UTC) if isinstance(ts, int | float) else ts

            results.append(
                MT5PositionInfo(
                    ticket=int(getattr(p, "ticket", 0)),
                    time=pos_time,
                    time_msc=int(getattr(p, "time_msc", 0)),
                    type=int(getattr(p, "type", 0)),
                    magic=int(getattr(p, "magic", 0)),
                    identifier=int(getattr(p, "identifier", 0)),
                    reason=int(getattr(p, "reason", 0)),
                    volume=float(getattr(p, "volume", 0.0)),
                    price_open=float(getattr(p, "price_open", 0.0)),
                    sl=float(getattr(p, "sl", 0.0)),
                    tp=float(getattr(p, "tp", 0.0)),
                    price_current=float(getattr(p, "price_current", 0.0)),
                    swap=float(getattr(p, "swap", 0.0)),
                    profit=float(getattr(p, "profit", 0.0)),
                    symbol=str(getattr(p, "symbol", "")),
                    comment=str(getattr(p, "comment", "")),
                    external_id=str(getattr(p, "external_id", "")),
                )
            )

        return results

    def shutdown(self) -> None:
        """Safely shuts down the terminal IPC connection and releases resources."""
        if self._is_initialized and self._mt5 is not None:
            try:
                self._mt5.shutdown()
                logger.info("MT5 terminal IPC connection terminated cleanly.")
            except Exception as exc:
                logger.warning(f"Exception during MT5 shutdown: {exc}")
            finally:
                self._is_initialized = False

    def run_diagnostics(self) -> MT5ConnectionDiagnostics:
        """Runs a safe diagnostic pass on the terminal connection and account."""
        self._ensure_client()
        terminal_status: MT5TerminalStatus | None = None
        account_status: MT5AccountInfo | None = None
        err_code: int | None = None
        err_desc: str | None = None

        if not self._is_initialized:
            try:
                self.initialize()
            except MT5InitializationError as e:
                err_code = e.details.get("error_code") if e.details else None
                err_desc = e.message
                return MT5ConnectionDiagnostics(
                    initialized=False,
                    terminal=None,
                    account=None,
                    error_code=err_code,
                    error_description=err_desc,
                    details={"path": self.terminal_path},
                )

        try:
            terminal_status = self.get_terminal_status()
        except MT5Error as e:
            err_code = e.details.get("error_code") if e.details else None
            err_desc = e.message

        try:
            account_status = self.get_account_info()
        except MT5AccountError as e:
            # Not an overall terminal failure if account is unauthenticated
            if err_code is None:
                err_code = e.details.get("error_code") if e.details else None
                err_desc = e.message

        return MT5ConnectionDiagnostics(
            initialized=self._is_initialized,
            terminal=terminal_status,
            account=account_status,
            error_code=err_code,
            error_description=err_desc,
            details={"path": self.terminal_path},
        )

    # -------------------------------------------------------------------------
    # Law of Read-Only Safety Guards
    # -------------------------------------------------------------------------
    def order_send(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Strictly prohibited: Application is read-only."""
        raise PermissionError(
            "Order execution is strictly forbidden by the Law of Read-Only Safety."
        )

    def order_check(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Strictly prohibited: Application is read-only."""
        raise PermissionError(
            "Order checking/placement is forbidden by the Law of Read-Only Safety."
        )

    def position_close(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Strictly prohibited: Application is read-only."""
        raise PermissionError(
            "Position closing is strictly forbidden by the Law of Read-Only Safety."
        )

    # -------------------------------------------------------------------------
    # Context Manager Protocols
    # -------------------------------------------------------------------------
    def __enter__(self) -> "MT5Connector":
        self.initialize()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.shutdown()
