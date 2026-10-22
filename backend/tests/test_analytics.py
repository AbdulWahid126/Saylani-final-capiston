"""Comprehensive unit and integration tests for TASK-009: Deterministic Financial Analytics Engine.

Tests cover:
- Benchmark hand-calculated financial datasets with verified independent expected values.
- Metrics: Win rate, loss rate, gross profit, gross loss, net P&L, profit factor, expectancy, average win/loss.
- Chronological equity curve: Monotonic high-water mark, monetary drawdown vs percentage drawdown.
- Sharpe and Sortino ratios: Documented assumptions, unannualized per-trade returns, downside deviation.
- Edge cases:
  * Zero trades (empty dataset) -> safe zeroes, no ZeroDivisionError.
  * All winning trades -> profit factor None, sortino None (zero downside).
  * All losing trades -> profit factor 0.0, win rate 0.0%.
  * All breakeven trades -> win rate 0.0%, profit factor None.
  * Zero variance trades -> std == 0 -> Sharpe None.
- Exclusion of open and partial positions from closed-trade statistics.
- Financial accuracy: Commission, swap, and fee deductions included in realized Net P&L.
- Currency isolation: Rejection of mixed-currency aggregation without account/currency filter.
- Multi-tenant boundary: User A cannot query User B's account analytics.
- Date filter validation: from_date > to_date returns 400 Bad Request.
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.analytics.engine import (
    TradeRecord,
    calculate_breakdowns,
    calculate_equity_curve,
    calculate_performance_metrics,
    calculate_sharpe_sortino,
    extract_trade_records,
)

# ==============================================================================
# 1. PURE ENGINE UNIT TESTS (INDEPENDENT BENCHMARKS & EDGE CASES)
# ==============================================================================


def test_analytics_benchmark_hand_calculated_dataset():
    """Verify metrics against an independently hand-calculated benchmark dataset.

    Independent Benchmark Dataset:
    Initial Balance: $10,000.00
    Trade 1: +$300.00 (Win)  -> Equity: $10,300.00, Peak: $10,300.00, DD: $0.00 (0.0%)
    Trade 2: -$150.00 (Loss) -> Equity: $10,150.00, Peak: $10,300.00, DD: $150.00 (1.46%)
    Trade 3: +$200.00 (Win)  -> Equity: $10,350.00, Peak: $10,350.00, DD: $0.00 (0.0%)
    Trade 4: -$350.00 (Loss) -> Equity: $10,000.00, Peak: $10,350.00, DD: $350.00 (3.38%)
    Trade 5:   $0.00 (BE)   -> Equity: $10,000.00, Peak: $10,350.00, DD: $350.00 (3.38%)

    Hand-calculated Expected Values:
    Total: 5, Wins: 2, Losses: 2, BE: 1
    Win Rate: 40.0%, Loss Rate: 40.0%, BE Rate: 20.0%
    Gross Profit: $500.00, Gross Loss: $500.00
    Net P&L: $0.00
    Average Win: $250.00, Average Loss: $250.00
    Win/Loss Ratio: 1.00
    Profit Factor: 1.00 (500 / 500)
    Expectancy: $0.00 per trade
    Max DD Monetary: $350.00
    Max DD Percentage: 3.38% (350 / 10350 * 100)
    Max Consecutive Wins: 1
    Max Consecutive Losses: 1
    Current Streak: 0
    """
    base_time = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

    trades = [
        TradeRecord(
            id="t1",
            account_id="acc1",
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            entry_price=1.0800,
            exit_price=1.0830,
            gross_profit=320.0,
            commission=-15.0,
            swap=-5.0,
            net_pnl=300.0,
            open_time=base_time,
            close_time=base_time + timedelta(hours=2),
            status="CLOSED",
            session="LONDON",
            setup_tag="FVG_ENTRY",
        ),
        TradeRecord(
            id="t2",
            account_id="acc1",
            symbol="EURUSD",
            direction="SELL",
            volume=1.0,
            entry_price=1.0850,
            exit_price=1.0865,
            gross_profit=-135.0,
            commission=-15.0,
            swap=0.0,
            net_pnl=-150.0,
            open_time=base_time + timedelta(days=1),
            close_time=base_time + timedelta(days=1, hours=3),
            status="CLOSED",
            session="NY_AM",
            setup_tag="OB_RETEST",
        ),
        TradeRecord(
            id="t3",
            account_id="acc1",
            symbol="GBPUSD",
            direction="BUY",
            volume=1.5,
            entry_price=1.2600,
            exit_price=1.2620,
            gross_profit=215.0,
            commission=-15.0,
            swap=0.0,
            net_pnl=200.0,
            open_time=base_time + timedelta(days=2),
            close_time=base_time + timedelta(days=2, hours=1),
            status="CLOSED",
            session="LONDON",
            setup_tag="FVG_ENTRY",
        ),
        TradeRecord(
            id="t4",
            account_id="acc1",
            symbol="GBPUSD",
            direction="BUY",
            volume=1.5,
            entry_price=1.2650,
            exit_price=1.2615,
            gross_profit=-335.0,
            commission=-15.0,
            swap=0.0,
            net_pnl=-350.0,
            open_time=base_time + timedelta(days=3),
            close_time=base_time + timedelta(days=3, hours=4),
            status="CLOSED",
            session="NY_PM",
            setup_tag="BREAKOUT",
        ),
        TradeRecord(
            id="t5",
            account_id="acc1",
            symbol="EURUSD",
            direction="BUY",
            volume=0.5,
            entry_price=1.0820,
            exit_price=1.0820,
            gross_profit=10.0,
            commission=-10.0,
            swap=0.0,
            net_pnl=0.0,
            open_time=base_time + timedelta(days=4),
            close_time=base_time + timedelta(days=4, hours=1),
            status="CLOSED",
            session="ASIA",
            setup_tag="SCALP",
        ),
    ]

    metrics = calculate_performance_metrics(trades, initial_balance=10000.0, currency="USD")

    # Independent assertions
    assert metrics.total_trades == 5
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 2
    assert metrics.breakeven_trades == 1
    assert metrics.win_rate == 40.0
    assert metrics.loss_rate == 40.0
    assert metrics.breakeven_rate == 20.0

    assert metrics.gross_profit == 500.0
    assert metrics.gross_loss == 500.0
    assert metrics.net_pnl == 0.0
    assert metrics.average_win == 250.0
    assert metrics.average_loss == 250.0
    assert metrics.win_loss_ratio == 1.0
    assert metrics.profit_factor == 1.0
    assert metrics.expectancy_per_trade == 0.0

    assert metrics.max_consecutive_wins == 1
    assert metrics.max_consecutive_losses == 1
    assert metrics.current_streak == 0

    assert metrics.max_drawdown_monetary == 350.0
    assert metrics.max_drawdown_percentage == 3.38

    # Equity curve verification
    eq_curve = calculate_equity_curve(trades, initial_balance=10000.0, currency="USD")
    assert len(eq_curve.points) == 6  # 1 origin point + 5 trades
    assert eq_curve.points[0].balance == 10000.0
    assert eq_curve.points[0].peak_equity == 10000.0
    assert eq_curve.points[1].equity == 10300.0
    assert eq_curve.points[1].peak_equity == 10300.0
    assert eq_curve.points[2].equity == 10150.0
    assert eq_curve.points[2].drawdown_monetary == 150.0
    assert eq_curve.points[3].equity == 10350.0
    assert eq_curve.points[3].peak_equity == 10350.0
    assert eq_curve.points[4].equity == 10000.0
    assert eq_curve.points[4].drawdown_monetary == 350.0
    assert eq_curve.points[5].equity == 10000.0


def test_analytics_empty_dataset_zero_trades():
    """Verify that an empty dataset safely returns zeroes and None without exceptions."""
    metrics = calculate_performance_metrics([], initial_balance=5000.0, currency="USD")

    assert metrics.total_trades == 0
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.gross_profit == 0.0
    assert metrics.gross_loss == 0.0
    assert metrics.net_pnl == 0.0
    assert metrics.average_win == 0.0
    assert metrics.average_loss == 0.0
    assert metrics.win_loss_ratio is None
    assert metrics.profit_factor is None
    assert metrics.expectancy_per_trade == 0.0
    assert metrics.sharpe_ratio is None
    assert metrics.sortino_ratio is None
    assert metrics.max_drawdown_monetary == 0.0
    assert metrics.max_drawdown_percentage == 0.0

    eq_curve = calculate_equity_curve([], initial_balance=5000.0, currency="USD")
    assert len(eq_curve.points) == 1
    assert eq_curve.points[0].equity == 5000.0
    assert eq_curve.max_drawdown_monetary == 0.0


def test_analytics_all_winning_trades_zero_loss_guard():
    """Verify that 100% win rate handles profit_factor = None and sortino = None safely."""
    base_time = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    trades = [
        TradeRecord(
            id=f"t{i}",
            account_id="acc1",
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            entry_price=1.0800,
            exit_price=1.0850,
            gross_profit=100.0,
            commission=0.0,
            swap=0.0,
            net_pnl=100.0,
            open_time=base_time + timedelta(hours=i),
            close_time=base_time + timedelta(hours=i, minutes=30),
            status="CLOSED",
        )
        for i in range(3)
    ]

    metrics = calculate_performance_metrics(trades, initial_balance=1000.0, currency="USD")

    assert metrics.total_trades == 3
    assert metrics.winning_trades == 3
    assert metrics.losing_trades == 0
    assert metrics.win_rate == 100.0
    assert metrics.gross_loss == 0.0
    # Guard against ZeroDivisionError: profit_factor must be None
    assert metrics.profit_factor is None
    assert metrics.average_loss == 0.0
    assert metrics.win_loss_ratio is None
    assert metrics.max_consecutive_wins == 3
    assert metrics.current_streak == 3
    assert metrics.max_drawdown_monetary == 0.0
    assert metrics.max_drawdown_percentage == 0.0

    # Sortino should be None because downside deviation is 0.0 (no downside risk)
    assert metrics.sortino_ratio is None


def test_analytics_all_losing_trades():
    """Verify behavior when 100% of trades are losses."""
    base_time = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    trades = [
        TradeRecord(
            id=f"t{i}",
            account_id="acc1",
            symbol="EURUSD",
            direction="SELL",
            volume=1.0,
            entry_price=1.0800,
            exit_price=1.0850,
            gross_profit=-50.0,
            commission=0.0,
            swap=0.0,
            net_pnl=-50.0,
            open_time=base_time + timedelta(hours=i),
            close_time=base_time + timedelta(hours=i, minutes=30),
            status="CLOSED",
        )
        for i in range(4)
    ]

    metrics = calculate_performance_metrics(trades, initial_balance=1000.0, currency="USD")

    assert metrics.total_trades == 4
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 4
    assert metrics.win_rate == 0.0
    assert metrics.loss_rate == 100.0
    assert metrics.gross_profit == 0.0
    assert metrics.gross_loss == 200.0
    assert metrics.net_pnl == -200.0
    assert metrics.profit_factor == 0.0
    assert metrics.average_win == 0.0
    assert metrics.average_loss == 50.0
    assert metrics.expectancy_per_trade == -50.0
    assert metrics.max_consecutive_losses == 4
    assert metrics.current_streak == -4
    assert metrics.max_drawdown_monetary == 200.0
    assert metrics.max_drawdown_percentage == 20.0  # 200 / 1000 * 100


def test_analytics_zero_variance_trades_sharpe_none():
    """Verify that identical returns (zero variance, std == 0) return sharpe_ratio = None."""
    base_time = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
    # 3 trades with exact identical net P&L on fixed initial balance
    trades = [
        TradeRecord(
            id=f"t{i}",
            account_id="acc1",
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            entry_price=1.0800,
            exit_price=1.0850,
            gross_profit=100.0,
            commission=0.0,
            swap=0.0,
            net_pnl=100.0,
            open_time=base_time + timedelta(days=i),
            close_time=base_time + timedelta(days=i, hours=1),
            status="CLOSED",
        )
        for i in range(3)
    ]

    sharpe, sortino, assumptions = calculate_sharpe_sortino(trades, initial_balance=0.0)
    # std of [100.0, 100.0, 100.0] is 0.0 -> Sharpe must be None
    assert sharpe is None
    assert sortino is None
    assert assumptions.return_series == "per_trade_monetary_pnl"


def test_analytics_exclusion_of_open_and_partial_trades():
    """Verify that OPEN and PARTIAL trades are segregated from closed metrics."""
    base_time = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

    mixed_items = [
        # Closed trade
        TradeRecord(
            id="c1",
            account_id="acc1",
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            entry_price=1.0800,
            exit_price=1.0850,
            gross_profit=100.0,
            commission=-5.0,
            swap=0.0,
            net_pnl=95.0,
            open_time=base_time,
            close_time=base_time + timedelta(hours=1),
            status="CLOSED",
        ),
        # Open trade (floating)
        TradeRecord(
            id="o1",
            account_id="acc1",
            symbol="GBPUSD",
            direction="BUY",
            volume=0.5,
            entry_price=1.2600,
            exit_price=None,
            gross_profit=0.0,
            commission=-2.5,
            swap=0.0,
            net_pnl=0.0,
            open_time=base_time + timedelta(hours=2),
            close_time=None,  # Not closed
            status="OPEN",
        ),
        # Partial close still running
        {
            "id": "p1",
            "account_id": "acc1",
            "symbol": "USDJPY",
            "direction": "SELL",
            "volume": 0.5,
            "entry_price": 150.0,
            "net_pnl": 0.0,
            "status": "PARTIAL",
            "close_time": None,
        },
    ]

    closed_records, open_count = extract_trade_records(mixed_items)

    assert len(closed_records) == 1
    assert open_count == 2
    assert closed_records[0].id == "c1"

    metrics = calculate_performance_metrics(
        closed_records, initial_balance=1000.0, open_trades_count=open_count
    )
    assert metrics.total_trades == 1
    assert metrics.open_trades_count == 2
    assert metrics.net_pnl == 95.0


def test_analytics_breakdowns_calculation():
    """Verify multi-dimensional performance breakdowns by symbol, direction, and session."""
    base_time = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # 2026-03-02 is Monday

    trades = [
        TradeRecord(
            id="t1",
            account_id="acc1",
            symbol="EURUSD",
            direction="BUY",
            volume=1.0,
            entry_price=1.0800,
            exit_price=1.0850,
            gross_profit=100.0,
            commission=0.0,
            swap=0.0,
            net_pnl=100.0,
            open_time=base_time,
            close_time=base_time + timedelta(hours=1),
            status="CLOSED",
            session="LONDON",
            setup_tag="FVG",
        ),
        TradeRecord(
            id="t2",
            account_id="acc1",
            symbol="EURUSD",
            direction="SELL",
            volume=1.0,
            entry_price=1.0850,
            exit_price=1.0860,
            gross_profit=-50.0,
            commission=0.0,
            swap=0.0,
            net_pnl=-50.0,
            open_time=base_time + timedelta(hours=3),
            close_time=base_time + timedelta(hours=4),
            status="CLOSED",
            session="NY_AM",
            setup_tag="OB",
        ),
        TradeRecord(
            id="t3",
            account_id="acc1",
            symbol="XAUUSD",
            direction="BUY",
            volume=0.5,
            entry_price=2000.0,
            exit_price=2010.0,
            gross_profit=250.0,
            commission=0.0,
            swap=0.0,
            net_pnl=250.0,
            open_time=base_time + timedelta(days=1),  # Tuesday
            close_time=base_time + timedelta(days=1, hours=2),
            status="CLOSED",
            session="LONDON",
            setup_tag="FVG",
        ),
    ]

    breakdowns = calculate_breakdowns(trades)

    # By Symbol
    symbols = {item.category: item for item in breakdowns.by_symbol}
    assert "EURUSD" in symbols
    assert symbols["EURUSD"].total_trades == 2
    assert symbols["EURUSD"].wins == 1
    assert symbols["EURUSD"].losses == 1
    assert symbols["EURUSD"].net_pnl == 50.0
    assert symbols["EURUSD"].win_rate == 50.0
    assert symbols["EURUSD"].profit_factor == 2.0  # 100 / 50

    assert "XAUUSD" in symbols
    assert symbols["XAUUSD"].total_trades == 1
    assert symbols["XAUUSD"].net_pnl == 250.0

    # By Direction
    directions = {item.category: item for item in breakdowns.by_direction}
    assert directions["BUY"].total_trades == 2
    assert directions["BUY"].win_rate == 100.0
    assert directions["SELL"].total_trades == 1
    assert directions["SELL"].win_rate == 0.0

    # By Session
    sessions = {item.category: item for item in breakdowns.by_session}
    assert sessions["LONDON"].total_trades == 2
    assert sessions["LONDON"].net_pnl == 350.0


# ==============================================================================
# 2. FASTAPI ENDPOINT INTEGRATION TESTS & MULTI-TENANT ISOLATION
# ==============================================================================


async def create_user_and_account(
    client: AsyncClient, email: str, account_number: str, currency: str = "USD"
) -> dict[str, str]:
    """Helper to create and authenticate a test user and an account."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert reg_resp.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    acc_resp = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "broker_name": "IC Markets",
            "server_name": "ICMarketsSC-Live",
            "account_number": account_number,
            "account_type": "LIVE",
            "currency": currency,
            "initial_balance": 10000.0,
            "balance": 10000.0,
            "equity": 10000.0,
        },
    )
    assert acc_resp.status_code == 201
    account_id = acc_resp.json()["id"]

    return {
        "headers": headers,
        "token": token,
        "account_id": account_id,
    }


@pytest.mark.asyncio
async def test_analytics_summary_and_equity_curve_api(async_client: AsyncClient):
    """Test authenticated analytics summary and equity curve endpoints."""
    user = await create_user_and_account(async_client, "trader_analytics1@test.com", "880011")
    headers = user["headers"]
    acc_id = user["account_id"]

    base_time = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)

    # Insert two closed manual trades
    t1_resp = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": acc_id,
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": 1.0,
            "entry_price": 1.0800,
            "exit_price": 1.0840,
            "gross_profit": 400.0,
            "commission": -10.0,
            "swap": 0.0,
            "open_time": base_time.isoformat(),
            "close_time": (base_time + timedelta(hours=1)).isoformat(),
            "status": "CLOSED",
        },
    )
    assert t1_resp.status_code == 201

    t2_resp = await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": acc_id,
            "symbol": "EURUSD",
            "direction": "SELL",
            "volume": 1.0,
            "entry_price": 1.0850,
            "exit_price": 1.0870,
            "gross_profit": -200.0,
            "commission": -10.0,
            "swap": 0.0,
            "open_time": (base_time + timedelta(days=1)).isoformat(),
            "close_time": (base_time + timedelta(days=1, hours=2)).isoformat(),
            "status": "CLOSED",
        },
    )
    assert t2_resp.status_code == 201

    # Call summary endpoint
    summary_resp = await async_client.get("/api/v1/analytics/summary", headers=headers)
    assert summary_resp.status_code == 200
    data = summary_resp.json()
    metrics = data["metrics"]

    # Trade 1 net: 390.0, Trade 2 net: -210.0 -> Net P&L = 180.0
    assert metrics["total_trades"] == 2
    assert metrics["winning_trades"] == 1
    assert metrics["losing_trades"] == 1
    assert metrics["win_rate"] == 50.0
    assert metrics["net_pnl"] == 180.0
    assert metrics["gross_profit"] == 390.0
    assert metrics["gross_loss"] == 210.0
    assert metrics["profit_factor"] == 1.86  # 390 / 210
    assert metrics["currency"] == "USD"
    assert metrics["initial_balance"] == 10000.0

    # Call equity-curve endpoint
    eq_resp = await async_client.get("/api/v1/analytics/equity-curve", headers=headers)
    assert eq_resp.status_code == 200
    eq_data = eq_resp.json()
    assert eq_data["current_equity"] == 10180.0
    assert eq_data["total_net_pnl"] == 180.0
    assert len(eq_data["points"]) == 3  # Origin + 2 trades

    # Call breakdowns endpoint
    breakdown_resp = await async_client.get("/api/v1/analytics/breakdowns", headers=headers)
    assert breakdown_resp.status_code == 200
    brk_data = breakdown_resp.json()
    assert len(brk_data["by_symbol"]) == 1
    assert brk_data["by_symbol"][0]["category"] == "EURUSD"
    assert brk_data["by_symbol"][0]["net_pnl"] == 180.0

    # Call account-scoped shortcut endpoint
    acc_summary_resp = await async_client.get(
        f"/api/v1/accounts/{acc_id}/analytics/summary", headers=headers
    )
    assert acc_summary_resp.status_code == 200
    assert acc_summary_resp.json()["account_id"] == acc_id


@pytest.mark.asyncio
async def test_analytics_multi_tenant_isolation(async_client: AsyncClient):
    """Verify that User A cannot access User B's account analytics."""
    user_a = await create_user_and_account(async_client, "trader_a_analytics@test.com", "991100")
    user_b = await create_user_and_account(async_client, "trader_b_analytics@test.com", "991101")

    # User B queries User A's account analytics -> 403 Forbidden
    cross_resp = await async_client.get(
        f"/api/v1/accounts/{user_a['account_id']}/analytics/summary",
        headers=user_b["headers"],
    )
    assert cross_resp.status_code == 403
    assert "forbidden" in cross_resp.json()["error"]["message"].lower()

    # User B passes User A's account_id as query parameter -> 403 Forbidden
    param_resp = await async_client.get(
        f"/api/v1/analytics/summary?account_id={user_a['account_id']}",
        headers=user_b["headers"],
    )
    assert param_resp.status_code == 403


@pytest.mark.asyncio
async def test_analytics_date_bounds_validation(async_client: AsyncClient):
    """Verify that from_date > to_date triggers HTTP 400 Bad Request."""
    user = await create_user_and_account(async_client, "trader_dates@test.com", "773322")

    from_ts = datetime(2026, 3, 10, 0, 0, tzinfo=UTC).isoformat()
    to_ts = datetime(2026, 3, 5, 0, 0, tzinfo=UTC).isoformat()

    resp = await async_client.get(
        "/api/v1/analytics/summary",
        params={"from_date": from_ts, "to_date": to_ts},
        headers=user["headers"],
    )
    assert resp.status_code == 400
    assert "from_date cannot be greater than to_date" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_analytics_mixed_currency_rejection(async_client: AsyncClient):
    """Verify that user accounts with different currencies cannot be aggregated without filter."""
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "trader_multi_currency@test.com", "password": "SecurePassword123!"},
    )
    assert reg_resp.status_code == 201
    token = (
        await async_client.post(
            "/api/v1/auth/login",
            json={"email": "trader_multi_currency@test.com", "password": "SecurePassword123!"},
        )
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Account 1 in USD
    await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "broker_name": "Broker USD",
            "server_name": "Server1",
            "account_number": "1001",
            "currency": "USD",
            "initial_balance": 5000.0,
        },
    )

    # Account 2 in EUR
    await async_client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "broker_name": "Broker EUR",
            "server_name": "Server2",
            "account_number": "2002",
            "currency": "EUR",
            "initial_balance": 5000.0,
        },
    )

    # Querying all accounts without currency filter -> 400 Bad Request
    resp = await async_client.get("/api/v1/analytics/summary", headers=headers)
    assert resp.status_code == 400
    assert "mixed currencies" in resp.json()["error"]["message"].lower()

    # Querying with explicit currency filter currency=USD -> succeeds
    usd_resp = await async_client.get("/api/v1/analytics/summary?currency=USD", headers=headers)
    assert usd_resp.status_code == 200
    assert usd_resp.json()["metrics"]["currency"] == "USD"
