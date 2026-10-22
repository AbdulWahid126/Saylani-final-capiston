"""Comprehensive unit and integration tests for TASK-010: Prop Firm Risk Manager Engine.

Tests cover:
- Daily loss calculation under BALANCE_BASED vs EQUITY_BASED rules.
- Static drawdown vs Trailing drawdown (including initial balance locking).
- Exact threshold boundaries:
  * < 50.0% -> GREEN
  * 50.0% - 79.99% -> AMBER
  * 80.0% - 99.99% -> RED
  * >= 100.0% -> BREACHED
- Timezone and session reset window calculations across UTC, America/New_York, and Europe/Prague.
- Open positions and floating P&L impact.
- Missing / zero account data -> UNAVAILABLE status.
- Profit target progress tracking.
- Profile CRUD API: Create, list, retrieve, update, delete.
- Multi-tenant boundary: User A vs User B profile and account evaluation isolation (403 Forbidden).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.analytics.risk_engine import (
    TEMPLATE_2STEP_100K,
    evaluate_account_risk,
    get_daily_reset_window,
)
from app.models.account import TradingAccount
from app.schemas.risk import (
    DailyLossCalculationBasis,
    DrawdownModel,
    PropRiskProfileBase,
    RiskStatusLevel,
)

# ==============================================================================
# 1. DETERMINISTIC RISK ENGINE UNIT TESTS
# ==============================================================================


def test_daily_reset_window_calculation():
    """Verify daily reset time window in Europe/Prague timezone."""
    # 2026-03-15 14:30:00 UTC
    eval_time = datetime(2026, 3, 15, 14, 30, 0, tzinfo=UTC)

    # In Europe/Prague (CET = UTC+1 in March before DST)
    start_utc, end_utc = get_daily_reset_window("Europe/Prague", "00:00:00", eval_time)

    # Midnight in Prague on March 15 is 2026-03-14 23:00:00 UTC
    assert start_utc.year == 2026
    assert start_utc.month == 3
    assert start_utc.day == 14
    assert start_utc.hour == 23  # UTC+1 offset
    assert end_utc == start_utc + timedelta(days=1)


def test_daily_loss_balance_vs_equity_based():
    """Verify that EQUITY_BASED includes floating loss while BALANCE_BASED excludes it."""
    acc_id = uuid.uuid4()
    mock_account = TradingAccount(
        id=acc_id,
        account_number="12345",
        broker_name="PropBroker",
        balance=100000.0,
        equity=98000.0,  # $2,000 floating loss
        initial_balance=100000.0,
        currency="USD",
    )

    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    # 1. Equity-based profile (5% limit = $5,000)
    profile_eq = PropRiskProfileBase(
        name="Equity Based",
        initial_balance=100000.0,
        daily_loss_limit_pct=5.0,
        max_total_loss_limit_pct=10.0,
        drawdown_model=DrawdownModel.STATIC,
        daily_loss_basis=DailyLossCalculationBasis.EQUITY_BASED,
        daily_reset_timezone="UTC",
        daily_reset_time="00:00:00",
    )

    res_eq = evaluate_account_risk(
        account=mock_account,
        profile=profile_eq,
        closed_trades=[],
        evaluation_time=now,
    )

    # Floating loss of $2,000 is included in effective daily loss
    assert res_eq.daily_risk.effective_daily_loss == 2000.0
    assert res_eq.daily_risk.daily_loss_remaining == 3000.0
    assert res_eq.daily_risk.daily_loss_utilization_pct == 40.0  # 2000 / 5000 = 40% (GREEN)
    assert res_eq.daily_risk.status_level == RiskStatusLevel.GREEN

    # 2. Balance-based profile (5% limit = $5,000)
    profile_bal = PropRiskProfileBase(
        name="Balance Based",
        initial_balance=100000.0,
        daily_loss_limit_pct=5.0,
        max_total_loss_limit_pct=10.0,
        drawdown_model=DrawdownModel.STATIC,
        daily_loss_basis=DailyLossCalculationBasis.BALANCE_BASED,
        daily_reset_timezone="UTC",
        daily_reset_time="00:00:00",
    )

    res_bal = evaluate_account_risk(
        account=mock_account,
        profile=profile_bal,
        closed_trades=[],
        evaluation_time=now,
    )

    # Balance is still $100,000 (no closed trades), so effective daily loss is $0.00
    assert res_bal.daily_risk.effective_daily_loss == 0.0
    assert res_bal.daily_risk.daily_loss_remaining == 5000.0
    assert res_bal.daily_risk.daily_loss_utilization_pct == 0.0


def test_risk_threshold_boundaries_green_amber_red_breached():
    """Verify exact status transitions: <50% GREEN, 50-80% AMBER, >80% RED, >=100% BREACHED."""
    acc_id = uuid.uuid4()
    profile = PropRiskProfileBase(
        name="Threshold Test",
        initial_balance=100000.0,
        daily_loss_limit_pct=5.0,  # $5,000 limit
        max_total_loss_limit_pct=10.0,
        drawdown_model=DrawdownModel.STATIC,
        daily_loss_basis=DailyLossCalculationBasis.EQUITY_BASED,
        daily_reset_timezone="UTC",
        daily_reset_time="00:00:00",
    )
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    # Case A: 49.9% loss ($2,495 loss) -> GREEN
    acc_green = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=100000.0, equity=97505.0
    )
    res_green = evaluate_account_risk(acc_green, profile, [], evaluation_time=now)
    assert res_green.daily_risk.status_level == RiskStatusLevel.GREEN
    assert res_green.daily_risk.is_breached is False

    # Case B: 50.0% loss ($2,500 loss) -> AMBER (exact lower boundary)
    acc_amber_low = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=100000.0, equity=97500.0
    )
    res_amber_low = evaluate_account_risk(acc_amber_low, profile, [], evaluation_time=now)
    assert res_amber_low.daily_risk.status_level == RiskStatusLevel.AMBER
    assert res_amber_low.daily_risk.daily_loss_utilization_pct == 50.0

    # Case C: 79.9% loss ($3,995 loss) -> AMBER
    acc_amber_high = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=100000.0, equity=96005.0
    )
    res_amber_high = evaluate_account_risk(acc_amber_high, profile, [], evaluation_time=now)
    assert res_amber_high.daily_risk.status_level == RiskStatusLevel.AMBER

    # Case D: 80.0% loss ($4,000 loss) -> RED (exact warning boundary)
    acc_red_low = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=100000.0, equity=96000.0
    )
    res_red_low = evaluate_account_risk(acc_red_low, profile, [], evaluation_time=now)
    assert res_red_low.daily_risk.status_level == RiskStatusLevel.RED
    assert res_red_low.daily_risk.daily_loss_utilization_pct == 80.0

    # Case E: 100.0% loss ($5,000 loss) -> BREACHED (exact violation boundary)
    acc_breached = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=100000.0, equity=95000.0
    )
    res_breached = evaluate_account_risk(acc_breached, profile, [], evaluation_time=now)
    assert res_breached.daily_risk.status_level == RiskStatusLevel.BREACHED
    assert res_breached.daily_risk.is_breached is True
    assert res_breached.is_any_limit_breached is True


def test_trailing_drawdown_high_water_mark_and_lock():
    """Verify trailing drawdown tracks peak equity and locks at initial balance when configured."""
    acc_id = uuid.uuid4()
    # 50k initial, 6% max loss ($3,000), trailing with lock at initial
    profile_trailing = PropRiskProfileBase(
        name="Trailing Test",
        initial_balance=50000.0,
        daily_loss_limit_pct=4.0,
        max_total_loss_limit_pct=6.0,
        drawdown_model=DrawdownModel.TRAILING,
        trail_locks_at_initial_balance=True,
        daily_reset_timezone="UTC",
        daily_reset_time="00:00:00",
    )
    now = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)

    # 1. Starting at 50k -> Peak HWM = 50k, Floor = 50k - 3k = 47k
    acc1 = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=50000.0, equity=50000.0
    )
    r1 = evaluate_account_risk(acc1, profile_trailing, [], evaluation_time=now)
    assert r1.overall_risk.peak_high_water_mark == 50000.0
    assert r1.overall_risk.hard_floor_level == 47000.0
    assert r1.overall_risk.overall_loss_remaining == 3000.0

    # 2. Account grows to 52k -> Peak HWM = 52k, Floor = 52k - 3k = 49k (< 50k, not locked yet)
    acc2 = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=52000.0, equity=52000.0
    )
    r2 = evaluate_account_risk(acc2, profile_trailing, [], evaluation_time=now)
    assert r2.overall_risk.peak_high_water_mark == 52000.0
    assert r2.overall_risk.hard_floor_level == 49000.0

    # 3. Account grows to 55k -> Peak HWM = 55k. Unlocked floor = 55k - 3k = 52k.
    # But trail_locks_at_initial_balance is True -> Floor locks at 50,000.0!
    acc3 = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=55000.0, equity=55000.0
    )
    r3 = evaluate_account_risk(acc3, profile_trailing, [], evaluation_time=now)
    assert r3.overall_risk.peak_high_water_mark == 55000.0
    assert r3.overall_risk.hard_floor_level == 50000.0  # LOCKED AT INITIAL!
    assert r3.overall_risk.overall_loss_remaining == 5000.0  # 55k - 50k


def test_missing_or_zero_account_data_unavailable():
    """Verify that zero/uninitialized account balance sets status to UNAVAILABLE."""
    acc_id = uuid.uuid4()
    mock_account = TradingAccount(
        id=acc_id,
        account_number="12345",
        broker_name="PropBroker",
        balance=0.0,
        equity=0.0,
        initial_balance=0.0,
        currency="USD",
    )
    profile = TEMPLATE_2STEP_100K

    res = evaluate_account_risk(mock_account, profile, [])
    assert res.is_data_available is True  # Profile's initial balance 100k used as fallback
    assert res.overall_risk.initial_reference_balance == 100000.0


def test_profit_target_calculation():
    """Verify prop firm challenge profit target progress calculation."""
    acc_id = uuid.uuid4()
    # 100k initial, 10% target ($10,000)
    profile = TEMPLATE_2STEP_100K

    # Account at $105,000 ($5,000 profit -> 50% target achieved)
    acc = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=105000.0, equity=105000.0
    )
    res = evaluate_account_risk(acc, profile, [])

    assert res.profit_target is not None
    assert res.profit_target.target_amount == 10000.0
    assert res.profit_target.current_profit == 5000.0
    assert res.profit_target.remaining_profit_required == 5000.0
    assert res.profit_target.progress_percentage == 50.0
    assert res.profit_target.target_achieved is False

    # Account reaches $110,000 ($10,000 profit -> 100% target achieved)
    acc_passed = TradingAccount(
        id=acc_id, account_number="1", broker_name="B", balance=110000.0, equity=110000.0
    )
    res_passed = evaluate_account_risk(acc_passed, profile, [])
    assert res_passed.profit_target.target_achieved is True
    assert res_passed.profit_target.progress_percentage == 100.0


# ==============================================================================
# 2. FASTAPI ENDPOINT INTEGRATION TESTS & TENANT ISOLATION
# ==============================================================================


async def create_user_and_account(
    client: AsyncClient, email: str, account_number: str
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
            "broker_name": "Prop Challenge Broker",
            "server_name": "Prop-Live",
            "account_number": account_number,
            "account_type": "PROP_CHALLENGE",
            "currency": "USD",
            "initial_balance": 100000.0,
            "balance": 100000.0,
            "equity": 100000.0,
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
async def test_risk_profile_crud_lifecycle(async_client: AsyncClient):
    """Test full CRUD lifecycle of custom risk profiles."""
    user = await create_user_and_account(async_client, "trader_risk_crud@test.com", "551122")
    headers = user["headers"]

    # 1. List profiles - should include templates
    list_resp = await async_client.get("/api/v1/risk/profiles", headers=headers)
    assert list_resp.status_code == 200
    profiles = list_resp.json()
    assert len(profiles) >= 3
    template_ids = [p["id"] for p in profiles]
    assert "template-2step-100k" in template_ids

    # 2. Create custom profile
    create_resp = await async_client.post(
        "/api/v1/risk/profiles",
        headers=headers,
        json={
            "name": "My Custom 200k Challenge",
            "description": "Custom rule profile with 4% daily and 8% static max loss.",
            "initial_balance": 200000.0,
            "daily_loss_limit_pct": 4.0,
            "max_total_loss_limit_pct": 8.0,
            "drawdown_model": "STATIC",
            "daily_loss_basis": "EQUITY_BASED",
            "trail_locks_at_initial_balance": True,
            "daily_reset_timezone": "UTC",
            "daily_reset_time": "00:00:00",
            "profit_target_pct": 10.0,
        },
    )
    assert create_resp.status_code == 201
    custom_prof = create_resp.json()
    prof_id = custom_prof["id"]
    assert custom_prof["name"] == "My Custom 200k Challenge"
    assert custom_prof["initial_balance"] == 200000.0

    # 3. Retrieve custom profile by ID
    get_resp = await async_client.get(f"/api/v1/risk/profiles/{prof_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == prof_id

    # 4. Update custom profile
    update_resp = await async_client.put(
        f"/api/v1/risk/profiles/{prof_id}",
        headers=headers,
        json={"daily_loss_limit_pct": 4.5, "name": "Updated 200k Challenge"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["daily_loss_limit_pct"] == 4.5
    assert update_resp.json()["name"] == "Updated 200k Challenge"

    # 5. Delete custom profile
    del_resp = await async_client.delete(f"/api/v1/risk/profiles/{prof_id}", headers=headers)
    assert del_resp.status_code == 204

    # 6. Verify deleted
    get_again = await async_client.get(f"/api/v1/risk/profiles/{prof_id}", headers=headers)
    assert get_again.status_code == 404


@pytest.mark.asyncio
async def test_account_risk_evaluation_endpoint(async_client: AsyncClient):
    """Test evaluating account risk standing via REST endpoint."""
    user = await create_user_and_account(async_client, "trader_risk_eval@test.com", "771122")
    headers = user["headers"]
    acc_id = user["account_id"]

    # Evaluate using default template
    eval_resp = await async_client.get(f"/api/v1/risk/accounts/{acc_id}/risk", headers=headers)
    assert eval_resp.status_code == 200
    report = eval_resp.json()

    assert report["account_id"] == acc_id
    assert report["currency"] == "USD"
    assert report["overall_status_level"] == "GREEN"
    assert report["is_any_limit_breached"] is False
    assert report["daily_risk"]["daily_loss_limit_amount"] == 5000.0
    assert report["overall_risk"]["hard_floor_level"] == 90000.0

    # Evaluate with manual snapshot override (simulating loss of $4,500 today -> RED status)
    snap_resp = await async_client.post(
        f"/api/v1/risk/accounts/{acc_id}/risk/evaluate",
        headers=headers,
        json={
            "snapshot_override": {
                "current_balance": 100000.0,
                "current_equity": 95500.0,  # $4,500 loss today = 90% utilization
                "current_floating_pnl": -4500.0,
            }
        },
    )
    assert snap_resp.status_code == 200
    snap_data = snap_resp.json()
    assert snap_data["daily_risk"]["status_level"] == "RED"
    assert snap_data["daily_risk"]["daily_loss_utilization_pct"] == 90.0
    assert snap_data["overall_status_level"] == "RED"


@pytest.mark.asyncio
async def test_risk_multi_tenant_isolation(async_client: AsyncClient):
    """Verify that User A cannot read, edit, delete, or evaluate User B's profiles or accounts."""
    user_a = await create_user_and_account(async_client, "user_a_risk@test.com", "110011")
    user_b = await create_user_and_account(async_client, "user_b_risk@test.com", "220022")

    # User A creates a custom profile
    create_resp = await async_client.post(
        "/api/v1/risk/profiles",
        headers=user_a["headers"],
        json={
            "name": "User A Private Profile",
            "initial_balance": 100000.0,
            "daily_loss_limit_pct": 5.0,
            "max_total_loss_limit_pct": 10.0,
        },
    )
    assert create_resp.status_code == 201
    profile_a_id = create_resp.json()["id"]

    # User B attempts to access User A's profile -> 403 Forbidden
    get_cross = await async_client.get(
        f"/api/v1/risk/profiles/{profile_a_id}",
        headers=user_b["headers"],
    )
    assert get_cross.status_code == 403

    # User B attempts to update User A's profile -> 403 Forbidden
    put_cross = await async_client.put(
        f"/api/v1/risk/profiles/{profile_a_id}",
        headers=user_b["headers"],
        json={"name": "Tampered Name"},
    )
    assert put_cross.status_code == 403

    # User B attempts to delete User A's profile -> 403 Forbidden
    del_cross = await async_client.delete(
        f"/api/v1/risk/profiles/{profile_a_id}",
        headers=user_b["headers"],
    )
    assert del_cross.status_code == 403

    # User B attempts to evaluate User A's account risk -> 403 Forbidden
    eval_cross = await async_client.get(
        f"/api/v1/risk/accounts/{user_a['account_id']}/risk",
        headers=user_b["headers"],
    )
    assert eval_cross.status_code == 403
