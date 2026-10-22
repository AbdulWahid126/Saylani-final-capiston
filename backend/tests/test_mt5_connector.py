"""Automated unit tests for MetaTrader 5 Windows IPC Connector.

Uses strict mocks for the MetaTrader 5 API so that test suites run deterministically
in any environment without requiring a live terminal or active broker login.
"""

from collections import namedtuple
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.errors import (
    MT5AccountError,
    MT5InitializationError,
    MT5QueryError,
)
from app.schemas.mt5 import (
    MT5AccountInfo,
    MT5ConnectionDiagnostics,
    MT5DealInfo,
    MT5PositionInfo,
    MT5TerminalStatus,
)
from app.services.mt5_connector import MT5Connector

# Namedtuples replicating MetaTrader5 C-extension structures
MockTerminalInfo = namedtuple(
    "MockTerminalInfo",
    [
        "connected",
        "trade_allowed",
        "build",
        "name",
        "path",
        "ping_last",
        "company",
        "community_account",
    ],
)

MockAccountInfo = namedtuple(
    "MockAccountInfo",
    [
        "login",
        "server",
        "currency",
        "balance",
        "equity",
        "profit",
        "margin",
        "margin_free",
        "margin_level",
        "leverage",
        "trade_mode",
        "company",
        "name",
        "trade_allowed",
    ],
)

MockTradeDeal = namedtuple(
    "MockTradeDeal",
    [
        "ticket",
        "order",
        "time",
        "time_msc",
        "type",
        "entry",
        "magic",
        "position_id",
        "reason",
        "volume",
        "price",
        "commission",
        "swap",
        "profit",
        "fee",
        "symbol",
        "comment",
        "external_id",
    ],
)

MockTradePosition = namedtuple(
    "MockTradePosition",
    [
        "ticket",
        "time",
        "time_msc",
        "type",
        "magic",
        "identifier",
        "reason",
        "volume",
        "price_open",
        "sl",
        "tp",
        "price_current",
        "swap",
        "profit",
        "symbol",
        "comment",
        "external_id",
    ],
)


@pytest.fixture
def mock_mt5():
    """Provides a fully mocked MetaTrader5 API client."""
    client = MagicMock()
    client.initialize.return_value = True
    client.last_error.return_value = (1, "Success")
    client.shutdown.return_value = None

    client.terminal_info.return_value = MockTerminalInfo(
        connected=True,
        trade_allowed=True,
        build=5020,
        name="MetaTrader 5",
        path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        ping_last=14500,
        company="MetaQuotes Ltd.",
        community_account=False,
    )

    client.account_info.return_value = MockAccountInfo(
        login=98765432,
        server="Demo-Server",
        currency="USD",
        balance=50000.0,
        equity=50850.25,
        profit=850.25,
        margin=1200.0,
        margin_free=49650.25,
        margin_level=4237.5,
        leverage=100,
        trade_mode=0,  # Demo
        company="Forex Brokerage LLC",
        name="Test Trader",
        trade_allowed=True,
    )

    return client


def test_initialization_success(mock_mt5):
    """Verifies successful MT5 terminal connection initialization."""
    connector = MT5Connector(terminal_path="C:\\mock\\terminal64.exe", mt5_client=mock_mt5)

    assert not connector.is_initialized
    # We pass an existing dummy or monkeypatch existence check
    res = connector.initialize(path="")
    assert res is True
    assert connector.is_initialized is True
    mock_mt5.initialize.assert_called_once()


def test_initialization_failure(mock_mt5):
    """Verifies that an initialization failure raises MT5InitializationError."""
    mock_mt5.initialize.return_value = False
    mock_mt5.last_error.return_value = (-6, "Terminal: Authorization failed")

    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)

    with pytest.raises(MT5InitializationError) as exc_info:
        connector.initialize()

    assert "Authorization failed" in exc_info.value.message
    assert exc_info.value.details["error_code"] == -6
    assert connector.is_initialized is False


def test_initialization_missing_executable(mock_mt5):
    """Verifies that a non-existent explicit path immediately errors before IPC call."""
    connector = MT5Connector(
        terminal_path="Z:\\NonExistent\\Path\\terminal64.exe", mt5_client=mock_mt5
    )

    with pytest.raises(MT5InitializationError) as exc_info:
        connector.initialize(path="Z:\\NonExistent\\Path\\terminal64.exe")

    assert "not found" in exc_info.value.message
    mock_mt5.initialize.assert_not_called()


def test_terminal_status_retrieval(mock_mt5):
    """Verifies retrieval and schema validation of terminal metadata."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    status = connector.get_terminal_status()
    assert isinstance(status, MT5TerminalStatus)
    assert status.connected is True
    assert status.build == 5020
    assert status.ping_last == 14500
    assert status.company == "MetaQuotes Ltd."


def test_account_info_retrieval_and_masking(mock_mt5):
    """Verifies account info schema parsing and sensitive login masking."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    acc = connector.get_account_info()
    assert isinstance(acc, MT5AccountInfo)
    assert acc.login == 98765432
    assert acc.masked_login == "987***32"
    assert acc.trade_mode_name == "Demo"
    assert acc.balance == 50000.0
    assert acc.equity == 50850.25
    assert acc.leverage == 100


def test_account_info_unauthorized_error(mock_mt5):
    """Verifies that missing account info raises MT5AccountError."""
    mock_mt5.account_info.return_value = None
    mock_mt5.last_error.return_value = (-6, "Terminal: Authorization failed")

    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    with pytest.raises(MT5AccountError) as exc_info:
        connector.get_account_info()

    assert "Failed to retrieve MT5 account info" in exc_info.value.message
    assert exc_info.value.details["error_code"] == -6


def test_historical_deals_retrieval(mock_mt5):
    """Verifies reading historical deals over a bounded date range."""
    now = datetime.now(UTC)
    ts1 = int((now - timedelta(days=2)).timestamp())
    ts2 = int((now - timedelta(days=1)).timestamp())

    mock_deals = (
        MockTradeDeal(
            ticket=1001,
            order=2001,
            time=ts1,
            time_msc=ts1 * 1000,
            type=0,  # DEAL_TYPE_BUY
            entry=0,  # DEAL_ENTRY_IN
            magic=12345,
            position_id=5001,
            reason=0,
            volume=1.5,
            price=1.08500,
            commission=-3.50,
            swap=0.0,
            profit=0.0,
            fee=0.0,
            symbol="EURUSD",
            comment="Entry Buy",
            external_id="",
        ),
        MockTradeDeal(
            ticket=1002,
            order=2002,
            time=ts2,
            time_msc=ts2 * 1000,
            type=1,  # DEAL_TYPE_SELL
            entry=1,  # DEAL_ENTRY_OUT
            magic=12345,
            position_id=5001,
            reason=0,
            volume=1.5,
            price=1.09200,
            commission=-3.50,
            swap=-1.20,
            profit=1050.00,
            fee=0.0,
            symbol="EURUSD",
            comment="Exit Sell",
            external_id="",
        ),
    )
    mock_mt5.history_deals_get.return_value = mock_deals

    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    deals = connector.get_historical_deals(
        date_from=now - timedelta(days=7),
        date_to=now,
    )

    assert len(deals) == 2
    assert isinstance(deals[0], MT5DealInfo)
    assert deals[0].ticket == 1001
    assert deals[0].symbol == "EURUSD"
    assert deals[0].volume == 1.5
    assert deals[1].profit == 1050.00
    assert deals[1].position_id == 5001


def test_historical_deals_empty_and_error(mock_mt5):
    """Verifies empty deal tuple handling versus fatal query errors."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    now = datetime.now(UTC)

    # Case 1: None returned but last_error is OK (no deals in range)
    mock_mt5.history_deals_get.return_value = None
    mock_mt5.last_error.return_value = (1, "Success")
    deals = connector.get_historical_deals(date_from=now - timedelta(days=1), date_to=now)
    assert deals == []

    # Case 2: None returned with actual terminal error
    mock_mt5.history_deals_get.return_value = None
    mock_mt5.last_error.return_value = (-1, "Terminal internal failure")
    with pytest.raises(MT5QueryError) as exc_info:
        connector.get_historical_deals(date_from=now - timedelta(days=1), date_to=now)
    assert "Failed to query historical deals" in exc_info.value.message


def test_historical_deals_invalid_range(mock_mt5):
    """Verifies that inverted date ranges are rejected before query."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    now = datetime.now(UTC)
    with pytest.raises(MT5QueryError) as exc_info:
        connector.get_historical_deals(date_from=now, date_to=now - timedelta(days=5))

    assert "Invalid date range" in exc_info.value.message
    mock_mt5.history_deals_get.assert_not_called()


def test_open_positions_diagnostic(mock_mt5):
    """Verifies diagnostic reading of open positions."""
    now = datetime.now(UTC)
    ts = int(now.timestamp())
    mock_positions = (
        MockTradePosition(
            ticket=8888,
            time=ts,
            time_msc=ts * 1000,
            type=0,  # BUY
            magic=0,
            identifier=8888,
            reason=0,
            volume=0.50,
            price_open=2350.20,
            sl=2340.00,
            tp=2380.00,
            price_current=2355.40,
            swap=-0.50,
            profit=260.00,
            symbol="XAUUSD",
            comment="Gold Buy",
            external_id="",
        ),
    )
    mock_mt5.positions_get.return_value = mock_positions

    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    connector.initialize()

    positions = connector.get_open_positions()
    assert len(positions) == 1
    assert isinstance(positions[0], MT5PositionInfo)
    assert positions[0].ticket == 8888
    assert positions[0].symbol == "XAUUSD"
    assert positions[0].profit == 260.00


def test_context_manager_guaranteed_shutdown(mock_mt5):
    """Verifies that entering and exiting context manager guarantees terminal shutdown."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)

    with connector as conn:
        assert conn.is_initialized is True

    assert connector.is_initialized is False
    mock_mt5.shutdown.assert_called_once()


def test_context_manager_shutdown_on_exception(mock_mt5):
    """Verifies that exceptions inside context manager still trigger clean shutdown."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)

    with pytest.raises(RuntimeError):
        with connector:
            raise RuntimeError("Simulated processing error")

    assert connector.is_initialized is False
    mock_mt5.shutdown.assert_called_once()


def test_read_only_safety_guardrails(mock_mt5):
    """Verifies that order execution and mutation methods are strictly forbidden."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)

    with pytest.raises(PermissionError) as exc_send:
        connector.order_send()
    assert "Law of Read-Only Safety" in str(exc_send.value)

    with pytest.raises(PermissionError) as exc_check:
        connector.order_check()
    assert "Law of Read-Only Safety" in str(exc_check.value)

    with pytest.raises(PermissionError) as exc_close:
        connector.position_close()
    assert "Law of Read-Only Safety" in str(exc_close.value)


def test_run_diagnostics(mock_mt5):
    """Verifies comprehensive diagnostic reporting."""
    connector = MT5Connector(terminal_path="", mt5_client=mock_mt5)
    diag = connector.run_diagnostics()

    assert isinstance(diag, MT5ConnectionDiagnostics)
    assert diag.initialized is True
    assert diag.terminal is not None
    assert diag.terminal.build == 5020
    assert diag.account is not None
    assert diag.account.masked_login == "987***32"
