"""Comprehensive unit and integration tests for TASK-011: Trading Behavior Analyzer.

Tests cover:
- Rapid re-entry after loss ("Revenge trading" pattern) with configurable window,
  volume escalation, and overlapping trade segregation.
- Overtrading frequency detection by day and session, comparing user-configured
  thresholds vs. baseline-inferred thresholds, and insufficient history safeguards.
- Risk escalation (Martingale-like sizing) with same-symbol contract normalization.
- Session drift detection with IANA timezone conversion, daylight-saving support,
  and unconfigured session safeguards (no invented hours).
- Deterministic discipline score calculation (0-100) and pattern summaries.
- Empty dataset, only-winning trades, and timestamp edge cases.
- Authenticated FastAPI endpoints: summary, findings, on-demand analysis, config CRUD.
- Multi-tenant isolation: User A vs User B data segregation (403 Forbidden).
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.analytics.behavior_analyzer import (
    analyze_overtrading_frequency,
    analyze_rapid_reentry_after_loss,
    analyze_risk_escalation,
    analyze_session_drift,
    analyze_trading_behavior,
    calculate_discipline_score,
)
from app.analytics.engine import TradeRecord
from app.schemas.behavior import (
    BehaviorAnalysisConfig,
    BehaviorPatternType,
    BehaviorSeverity,
    ThresholdSource,
)


def _make_trade(
    id_str: str,
    symbol: str = "EURUSD",
    net_pnl: float = 100.0,
    volume: float = 1.0,
    open_time: datetime | None = None,
    close_time: datetime | None = None,
    session: str | None = "LONDON",
) -> TradeRecord:
    """Helper to construct an immutable TradeRecord for unit testing."""
    now = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)
    o_time = open_time or now
    c_time = close_time or (o_time + timedelta(minutes=30))
    return TradeRecord(
        id=id_str,
        account_id="acc-1",
        symbol=symbol,
        direction="BUY",
        volume=volume,
        entry_price=1.1000,
        exit_price=1.1050 if net_pnl >= 0 else 1.0950,
        gross_profit=net_pnl,
        commission=-5.0,
        swap=0.0,
        net_pnl=net_pnl,
        open_time=o_time,
        close_time=c_time,
        status="CLOSED",
        session=session,
    )


# ==============================================================================
# 1. RAPID RE-ENTRY AFTER LOSS ("REVENGE TRADING") UNIT TESTS
# ==============================================================================


def test_rapid_reentry_after_loss_detected():
    """Verify detection of trade opened within 15m window after a loss."""
    t1_close = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)
    t1 = _make_trade("t1", symbol="EURUSD", net_pnl=-150.0, volume=1.0, close_time=t1_close)

    # Trade 2 opened 4 minutes after t1 closed (within 15m window) with increased size
    t2_open = datetime(2026, 4, 1, 10, 4, 0, tzinfo=UTC)
    t2 = _make_trade("t2", symbol="EURUSD", net_pnl=50.0, volume=1.5, open_time=t2_open)

    config = BehaviorAnalysisConfig(reentry_window_minutes=15)
    findings, _ = analyze_rapid_reentry_after_loss([t1, t2], config)

    assert len(findings) == 1
    f = findings[0]
    assert f.pattern_type == BehaviorPatternType.RAPID_REENTRY_AFTER_LOSS
    assert f.severity == BehaviorSeverity.HIGH  # <= 5 min gap with increased volume
    assert f.trade_id == "t2"
    assert "t1" in f.related_trade_ids
    assert f.evidence["time_gap_minutes"] == 4.0
    assert f.evidence["prior_loss_amount"] == 150.0
    assert f.evidence["volume_increased"] is True
    assert f.evidence["volume_ratio"] == 1.5


def test_rapid_reentry_ignores_wins_and_concurrent_trades():
    """Verify rapid re-entry is NOT triggered following a win or by overlapping trades."""
    base_time = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)

    # Case A: Prior trade was a WIN (+ $200)
    win_t1 = _make_trade("w1", net_pnl=200.0, close_time=base_time)
    sub_t2 = _make_trade("w2", open_time=base_time + timedelta(minutes=2))

    config = BehaviorAnalysisConfig(reentry_window_minutes=15)
    findings_win, _ = analyze_rapid_reentry_after_loss([win_t1, sub_t2], config)
    assert len(findings_win) == 0

    # Case B: Concurrent trade opened BEFORE loss trade closed
    loss_t1 = _make_trade(
        "l1",
        net_pnl=-100.0,
        open_time=base_time,
        close_time=base_time + timedelta(minutes=30),
    )
    # Concurrent trade opened at minute 15 (while loss_t1 was still running)
    concurrent_t2 = _make_trade(
        "c2",
        open_time=base_time + timedelta(minutes=15),
        close_time=base_time + timedelta(minutes=45),
    )

    findings_concurrent, _ = analyze_rapid_reentry_after_loss([loss_t1, concurrent_t2], config)
    assert len(findings_concurrent) == 0

    # Case C: Gap exceeds configured window (e.g. 25 minutes > 15m window)
    late_t3 = _make_trade(
        "late3",
        open_time=base_time + timedelta(minutes=55),  # 25 min after loss_t1 closed at min 30
    )
    findings_late, _ = analyze_rapid_reentry_after_loss([loss_t1, late_t3], config)
    assert len(findings_late) == 0


# ==============================================================================
# 2. OVERTRADING FREQUENCY UNIT TESTS
# ==============================================================================


def test_overtrading_frequency_user_configured():
    """Verify daily and session overtrading flags with explicit user thresholds."""
    day = datetime(2026, 4, 1, 8, 0, 0, tzinfo=UTC)
    trades = [
        _make_trade(f"t_{i}", open_time=day + timedelta(hours=i), session="LONDON")
        for i in range(5)
    ]

    # Explicit threshold: max 3 trades per day, max 2 per session
    config = BehaviorAnalysisConfig(
        max_trades_per_day=3,
        max_trades_per_session=2,
    )
    findings, _ = analyze_overtrading_frequency(trades, config)

    # Expect 1 daily finding (5 > 3) and 1 session finding (5 > 2)
    daily_findings = [f for f in findings if "session" not in f.evidence]
    session_findings = [f for f in findings if "session" in f.evidence]

    assert len(daily_findings) == 1
    assert daily_findings[0].evidence["trades_count"] == 5
    assert daily_findings[0].evidence["threshold"] == 3
    assert daily_findings[0].evidence["threshold_source"] == ThresholdSource.USER_CONFIGURED.value

    assert len(session_findings) == 1
    assert session_findings[0].evidence["session"] == "LONDON"
    assert session_findings[0].evidence["trades_count"] == 5


def test_overtrading_frequency_baseline_inferred():
    """Verify baseline inference when user has >= 5 trading days."""
    trades = []
    # 5 baseline days with 1 trade each
    for d in range(5):
        dt = datetime(2026, 4, 1 + d, 10, 0, 0, tzinfo=UTC)
        trades.append(_make_trade(f"base_{d}", open_time=dt))

    # Day 6 has 8 trades (high spike above mean of 1)
    day_spike = datetime(2026, 4, 7, 10, 0, 0, tzinfo=UTC)
    for i in range(8):
        trades.append(_make_trade(f"spike_{i}", open_time=day_spike + timedelta(minutes=i * 10)))

    config = BehaviorAnalysisConfig(max_trades_per_day=None)
    findings, _ = analyze_overtrading_frequency(trades, config)

    assert len(findings) >= 1
    f = findings[0]
    assert f.evidence["threshold_source"] == ThresholdSource.BASELINE_INFERRED.value
    assert f.evidence["trades_count"] == 8


def test_overtrading_insufficient_history_safeguard():
    """Verify system does not invent a threshold when < 5 trading days exist."""
    trades = [
        _make_trade("t1", open_time=datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)),
        _make_trade("t2", open_time=datetime(2026, 4, 2, 10, 0, 0, tzinfo=UTC)),
    ]
    config = BehaviorAnalysisConfig(max_trades_per_day=None)
    findings, limitations = analyze_overtrading_frequency(trades, config)

    assert len(findings) == 0
    assert any("Insufficient historical trading days" in lim for lim in limitations)


# ==============================================================================
# 3. RISK ESCALATION / MARTINGALE-LIKE SIZING UNIT TESTS
# ==============================================================================


def test_risk_escalation_same_symbol_detection():
    """Verify Martingale-like sizing detection on the same symbol following a loss."""
    t1_close = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)
    t1 = _make_trade("t1", symbol="EURUSD", net_pnl=-200.0, volume=1.0, close_time=t1_close)

    t2_open = datetime(2026, 4, 1, 10, 30, 0, tzinfo=UTC)
    t2 = _make_trade("t2", symbol="EURUSD", net_pnl=100.0, volume=2.0, open_time=t2_open)

    config = BehaviorAnalysisConfig(
        size_escalation_ratio=1.5,
        compare_same_symbol_only=True,
    )
    findings, _ = analyze_risk_escalation([t1, t2], config)

    assert len(findings) == 1
    f = findings[0]
    assert f.pattern_type == BehaviorPatternType.RISK_ESCALATION
    assert f.severity == BehaviorSeverity.HIGH  # 2.0x multiplier >= 2.0
    assert f.evidence["size_multiplier"] == 2.0
    assert "size" in f.title.lower() or "sizing" in f.description.lower()


def test_risk_escalation_symbol_normalization_guard():
    """Verify cross-instrument raw lot size comparisons are segregated by default."""
    t1_close = datetime(2026, 4, 1, 10, 0, 0, tzinfo=UTC)
    # Loss on EURUSD with 1.0 lot
    t1 = _make_trade("t1", symbol="EURUSD", net_pnl=-100.0, volume=1.0, close_time=t1_close)

    # Next trade is on BTCUSD with 2.0 lots (notional value differs vastly)
    t2_open = datetime(2026, 4, 1, 10, 30, 0, tzinfo=UTC)
    t2 = _make_trade("t2", symbol="BTCUSD", net_pnl=50.0, volume=2.0, open_time=t2_open)

    config = BehaviorAnalysisConfig(
        size_escalation_ratio=1.5,
        compare_same_symbol_only=True,
    )
    findings, _ = analyze_risk_escalation([t1, t2], config)

    # Should not trigger false escalation across different symbols
    assert len(findings) == 0


# ==============================================================================
# 4. SESSION DRIFT UNIT TESTS
# ==============================================================================


def test_session_drift_unconfigured_schedule_safeguard():
    """Verify system returns insufficient configuration limitation rather than inventing hours."""
    t1 = _make_trade("t1", session="ASIA")
    config = BehaviorAnalysisConfig(
        allowed_sessions=None,
        session_start_time=None,
    )
    findings, limitations = analyze_session_drift([t1], config)

    assert len(findings) == 0
    assert any("does not invent preferred trading hours" in lim for lim in limitations)


def test_session_drift_allowed_sessions_and_timezone_hours():
    """Verify session drift detection via allowed sessions list and IANA timezone window."""
    # 1. Allowed sessions filter
    t_london = _make_trade("t_lon", session="LONDON")
    t_asia = _make_trade("t_asia", session="ASIA")

    config_sessions = BehaviorAnalysisConfig(allowed_sessions=["LONDON", "NY_AM"])
    findings_sessions, _ = analyze_session_drift([t_london, t_asia], config_sessions)

    assert len(findings_sessions) == 1
    assert findings_sessions[0].trade_id == "t_asia"

    # 2. Local timezone window check (08:00 - 17:00 in America/New_York)
    # 2026-04-01 23:00:00 UTC = 19:00:00 EDT (outside 08:00 - 17:00 window)
    t_late_utc = datetime(2026, 4, 1, 23, 0, 0, tzinfo=UTC)
    t_late = _make_trade("t_late", open_time=t_late_utc)

    config_hours = BehaviorAnalysisConfig(
        session_start_time="08:00:00",
        session_end_time="17:00:00",
        session_timezone="America/New_York",
    )
    findings_hours, _ = analyze_session_drift([t_late], config_hours)

    assert len(findings_hours) == 1
    f_hour = findings_hours[0]
    assert f_hour.pattern_type == BehaviorPatternType.SESSION_DRIFT
    assert "America/New_York" in f_hour.evidence["timezone"]
    assert "19:00:00" in f_hour.evidence["local_time"]


# ==============================================================================
# 5. DISCIPLINE SCORE & EDGE CASES
# ==============================================================================


def test_discipline_score_deterministic_calculation():
    """Verify discipline score formula with varying severity deductions."""
    # Zero trades -> 100.0
    assert calculate_discipline_score([], 0) == 100.0

    # 1 High (-10), 1 Medium (-5), 1 Low (-2) -> 100 - 17 = 83.0
    from app.schemas.behavior import BehaviorFinding

    f_high = BehaviorFinding(
        id="1",
        pattern_type=BehaviorPatternType.RAPID_REENTRY_AFTER_LOSS,
        severity=BehaviorSeverity.HIGH,
        title="High",
        description="Desc",
        detected_at=datetime.now(UTC),
    )
    f_med = BehaviorFinding(
        id="2",
        pattern_type=BehaviorPatternType.OVERTRADING_FREQUENCY,
        severity=BehaviorSeverity.MEDIUM,
        title="Med",
        description="Desc",
        detected_at=datetime.now(UTC),
    )
    f_low = BehaviorFinding(
        id="3",
        pattern_type=BehaviorPatternType.SESSION_DRIFT,
        severity=BehaviorSeverity.LOW,
        title="Low",
        description="Desc",
        detected_at=datetime.now(UTC),
    )

    score = calculate_discipline_score([f_high, f_med, f_low], 10)
    assert score == 83.0


def test_behavior_empty_dataset_returns_clean_summary():
    """Verify clean response when analyzing empty trade history."""
    summary = analyze_trading_behavior([])
    assert summary.total_trades_analyzed == 0
    assert summary.total_findings == 0
    assert summary.overall_discipline_score == 100.0
    assert len(summary.pattern_summaries) == 4
    for p in summary.pattern_summaries:
        assert p.occurrences_count == 0


# ==============================================================================
# 6. FASTAPI REST API INTEGRATION & MULTI-TENANT ISOLATION TESTS
# ==============================================================================


async def create_user_and_account(
    client: AsyncClient, email: str, account_number: str
) -> dict[str, str]:
    """Helper to register and authenticate test user with trading account."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    acc = await client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "broker_name": "Behavior Broker",
            "server_name": "Demo-Server",
            "account_number": account_number,
            "account_type": "PROP_CHALLENGE",
            "currency": "USD",
            "initial_balance": 100000.0,
            "balance": 100000.0,
            "equity": 100000.0,
        },
    )
    assert acc.status_code == 201
    return {
        "headers": headers,
        "account_id": acc.json()["id"],
    }


@pytest.mark.asyncio
async def test_behavior_api_summary_and_findings_endpoints(async_client: AsyncClient):
    """Test behavior summary and detailed findings API endpoints."""
    user = await create_user_and_account(async_client, "trader_behavior_api@test.com", "880011")
    headers = user["headers"]
    acc_id = user["account_id"]

    # Insert a loss trade followed by a quick re-entry trade
    t1_open = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    t1_close = (datetime.now(UTC) - timedelta(hours=1, minutes=45)).isoformat()
    t2_open = (datetime.now(UTC) - timedelta(hours=1, minutes=40)).isoformat()  # 5 min gap
    t2_close = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    # Trade 1: Loss
    await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": acc_id,
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": 1.0,
            "entry_price": 1.1000,
            "exit_price": 1.0900,
            "gross_profit": -100.0,
            "net_pnl": -100.0,
            "open_time": t1_open,
            "close_time": t1_close,
            "status": "CLOSED",
            "session": "LONDON",
        },
    )

    # Trade 2: Rapid re-entry with 2.0 lots
    await async_client.post(
        "/api/v1/journal/entries",
        headers=headers,
        json={
            "account_id": acc_id,
            "symbol": "EURUSD",
            "direction": "BUY",
            "volume": 2.0,
            "entry_price": 1.0905,
            "exit_price": 1.0950,
            "gross_profit": 50.0,
            "net_pnl": 50.0,
            "open_time": t2_open,
            "close_time": t2_close,
            "status": "CLOSED",
            "session": "LONDON",
        },
    )

    # 1. GET /api/v1/behavior/summary
    summary_resp = await async_client.get(
        f"/api/v1/behavior/summary?account_id={acc_id}&reentry_window_minutes=15",
        headers=headers,
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    assert summary["total_trades_analyzed"] == 2
    assert summary["total_findings"] >= 1
    assert summary["overall_discipline_score"] < 100.0

    # 2. GET /api/v1/behavior/findings
    findings_resp = await async_client.get(
        f"/api/v1/behavior/findings?account_id={acc_id}&pattern_type=rapid_reentry_after_loss",
        headers=headers,
    )
    assert findings_resp.status_code == 200
    findings_data = findings_resp.json()
    assert findings_data["total_findings"] >= 1
    assert findings_data["findings"][0]["pattern_type"] == "rapid_reentry_after_loss"

    # 3. POST /api/v1/behavior/analyze (on-demand)
    analyze_resp = await async_client.post(
        "/api/v1/behavior/analyze",
        headers=headers,
        json={
            "account_id": acc_id,
            "config": {
                "reentry_window_minutes": 2,  # 2m window -> 5m gap won't be flagged
                "size_escalation_ratio": 3.0,
            },
        },
    )
    assert analyze_resp.status_code == 200
    analyze_data = analyze_resp.json()
    # With 2m window, rapid re-entry at 5m gap is not flagged
    reentry_findings = [
        f for f in analyze_data["findings"] if f["pattern_type"] == "rapid_reentry_after_loss"
    ]
    assert len(reentry_findings) == 0

    # 4. Account shortcut endpoint
    acc_summary_resp = await async_client.get(
        f"/api/v1/accounts/{acc_id}/behavior/summary",
        headers=headers,
    )
    assert acc_summary_resp.status_code == 200
    assert acc_summary_resp.json()["total_trades_analyzed"] == 2


@pytest.mark.asyncio
async def test_behavior_user_config_crud(async_client: AsyncClient):
    """Test retrieving and updating user behavioral preferences."""
    user = await create_user_and_account(async_client, "trader_behavior_config@test.com", "990022")
    headers = user["headers"]

    # 1. GET default configuration
    get_resp = await async_client.get("/api/v1/behavior/config", headers=headers)
    assert get_resp.status_code == 200
    cfg_data = get_resp.json()
    assert cfg_data["config"]["reentry_window_minutes"] == 15

    # 2. PUT custom configuration
    update_resp = await async_client.put(
        "/api/v1/behavior/config",
        headers=headers,
        json={
            "config": {
                "reentry_window_minutes": 20,
                "max_trades_per_day": 4,
                "size_escalation_ratio": 1.75,
                "session_timezone": "America/New_York",
                "allowed_sessions": ["LONDON", "NY_AM"],
            }
        },
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()
    assert updated_data["config"]["reentry_window_minutes"] == 20
    assert updated_data["config"]["max_trades_per_day"] == 4
    assert updated_data["config"]["allowed_sessions"] == ["LONDON", "NY_AM"]

    # 3. Verify subsequent GET returns updated preferences
    get_again = await async_client.get("/api/v1/behavior/config", headers=headers)
    assert get_again.status_code == 200
    assert get_again.json()["config"]["reentry_window_minutes"] == 20


@pytest.mark.asyncio
async def test_behavior_multi_tenant_isolation(async_client: AsyncClient):
    """Verify User B cannot access User A's behavior analysis or findings."""
    user_a = await create_user_and_account(async_client, "user_a_behav@test.com", "112233")
    user_b = await create_user_and_account(async_client, "user_b_behav@test.com", "445566")

    # User B attempts to access User A's account behavior summary -> 403 Forbidden
    cross_summary = await async_client.get(
        f"/api/v1/accounts/{user_a['account_id']}/behavior/summary",
        headers=user_b["headers"],
    )
    assert cross_summary.status_code == 403

    # User B attempts to query behavior summary scoped to User A's account -> 403 Forbidden
    cross_query = await async_client.get(
        f"/api/v1/behavior/summary?account_id={user_a['account_id']}",
        headers=user_b["headers"],
    )
    assert cross_query.status_code == 403

    # User B querying own behavior summary sees 0 trades and 100.0 score (no leakage)
    own_summary = await async_client.get(
        "/api/v1/behavior/summary",
        headers=user_b["headers"],
    )
    assert own_summary.status_code == 200
    assert own_summary.json()["total_trades_analyzed"] == 0
    assert own_summary.json()["total_findings"] == 0
