from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, computed_field


class MT5TerminalStatus(BaseModel):
    """Sanitized terminal connection status and metadata."""

    connected: bool = Field(
        ..., description="Whether the terminal is currently connected to a trade server"
    )
    trade_allowed: bool = Field(
        ..., description="Whether automated trading is permitted by terminal configuration"
    )
    build: int = Field(..., description="MetaTrader 5 terminal build number")
    name: str = Field(..., description="Terminal application name")
    path: str = Field(..., description="Absolute path to terminal executable")
    ping_last: int = Field(0, description="Last recorded network ping in microseconds")
    company: str = Field("", description="Broker or software distributor company name")
    community_account: bool = Field(
        False, description="Whether MQL5 community account is connected"
    )


class MT5AccountInfo(BaseModel):
    """Sanitized, read-only trading account details."""

    login: int = Field(..., description="Trading account numeric login ID")
    server: str = Field(..., description="Broker trade server name")
    currency: str = Field(..., description="Account base deposit currency")
    balance: float = Field(..., description="Account balance")
    equity: float = Field(..., description="Account equity")
    profit: float = Field(..., description="Current floating profit/loss")
    margin: float = Field(..., description="Margin currently utilized")
    margin_free: float = Field(..., description="Available free margin")
    margin_level: float | None = Field(None, description="Margin level percentage")
    leverage: int = Field(..., description="Account leverage ratio")
    trade_mode: int = Field(..., description="0 = Demo, 1 = Contest, 2 = Real")
    company: str = Field("", description="Brokerage company name")
    name: str = Field("", description="Client account name")
    trade_allowed: bool = Field(False, description="Whether trading is allowed for this account")

    @computed_field
    @property
    def masked_login(self) -> str:
        """Returns login identifier with sensitive middle digits masked."""
        s = str(self.login)
        if len(s) <= 4:
            return "***" + s[-1:] if len(s) > 1 else "***"
        return f"{s[:3]}***{s[-2:]}"

    @computed_field
    @property
    def trade_mode_name(self) -> str:
        """Returns human-readable trade mode name."""
        modes = {0: "Demo", 1: "Contest", 2: "Real"}
        return modes.get(self.trade_mode, "Unknown")


class MT5DealInfo(BaseModel):
    """Read-only representation of an MT5 historical deal transaction."""

    ticket: int = Field(..., description="Deal ticket number")
    order: int = Field(..., description="Originating order ticket number")
    time: datetime = Field(..., description="Deal execution timestamp (UTC)")
    time_msc: int = Field(0, description="Deal timestamp in milliseconds")
    type: int = Field(..., description="Deal type (0=BUY, 1=SELL, 2=BALANCE, etc.)")
    entry: int = Field(..., description="Deal entry direction (0=IN, 1=OUT, 2=INOUT, 3=OUT_BY)")
    magic: int = Field(0, description="Expert Advisor magic number")
    position_id: int = Field(..., description="Position ticket to which the deal belongs")
    reason: int = Field(0, description="Deal reason code")
    volume: float = Field(..., description="Executed volume in lots")
    price: float = Field(..., description="Deal execution price")
    commission: float = Field(0.0, description="Deal commission")
    swap: float = Field(0.0, description="Accumulated swap")
    profit: float = Field(0.0, description="Realized net profit/loss")
    fee: float = Field(0.0, description="Additional broker fee")
    symbol: str = Field(..., description="Instrument symbol (e.g. EURUSD)")
    comment: str = Field("", description="Deal comment")
    external_id: str = Field("", description="External system deal ID")


class MT5PositionInfo(BaseModel):
    """Diagnostic read-only representation of an active open position."""

    ticket: int = Field(..., description="Position ticket number")
    time: datetime = Field(..., description="Position open timestamp (UTC)")
    time_msc: int = Field(0, description="Timestamp in milliseconds")
    type: int = Field(..., description="Position type (0=BUY, 1=SELL)")
    magic: int = Field(0, description="Expert Advisor magic number")
    identifier: int = Field(..., description="Unique position identifier across lifecycle")
    reason: int = Field(0, description="Position open reason code")
    volume: float = Field(..., description="Current position volume in lots")
    price_open: float = Field(..., description="Volume-weighted open price")
    sl: float = Field(0.0, description="Current Stop Loss level")
    tp: float = Field(0.0, description="Current Take Profit level")
    price_current: float = Field(..., description="Current market price")
    swap: float = Field(0.0, description="Accumulated swap")
    profit: float = Field(0.0, description="Current unrealized floating profit")
    symbol: str = Field(..., description="Instrument symbol")
    comment: str = Field("", description="Position comment")
    external_id: str = Field("", description="External identifier")


class MT5ConnectionDiagnostics(BaseModel):
    """Comprehensive diagnostic status of the MT5 terminal IPC connection."""

    initialized: bool = Field(..., description="Whether MT5 IPC initialized successfully")
    terminal: MT5TerminalStatus | None = Field(None, description="Terminal status if available")
    account: MT5AccountInfo | None = Field(None, description="Account info if authorized")
    error_code: int | None = Field(None, description="MT5 error code if failure occurred")
    error_description: str | None = Field(
        None, description="MT5 error description if failure occurred"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional diagnostic context"
    )
