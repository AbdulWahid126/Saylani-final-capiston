"""Deterministic Trading Behavior Analyzer Engine.

Identifies objective, evidence-based patterns in a trader's historical activity:
1. Rapid Re-entry After Loss ("Revenge Trading" pattern)
2. Overtrading Frequency (by calendar day and session)
3. Risk Escalation / Martingale-like Sizing after loss
4. Session Drift (trades executed outside user-configured hours/sessions)

ZERO LLM MATH & ZERO PSYCHOANALYSIS:
All numerical calculations run in pure deterministic Python. Findings are strictly
factual and statistical, never offering clinical or psychological diagnoses.
"""

import math
import uuid
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import numpy as np

from app.analytics.engine import TradeRecord, _sort_trades_chronological, extract_trade_records
from app.models.journal import JournalEntry
from app.schemas.behavior import (
    BehaviorAnalysisConfig,
    BehaviorFinding,
    BehaviorPatternSummary,
    BehaviorPatternType,
    BehaviorSeverity,
    BehaviorSummaryResponse,
    ThresholdSource,
)
from app.schemas.common import DataClassificationBadge


def _ensure_timezone(dt: datetime | None, default_tz: ZoneInfo | None = None) -> datetime | None:
    """Ensure datetime has timezone information, defaulting to UTC if naive."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz or UTC)
    return dt


def _parse_time_str(time_str: str | None) -> time | None:
    """Parse 'HH:MM:SS' or 'HH:MM' string into datetime.time object."""
    if not time_str:
        return None
    try:
        parts = [int(p) for p in time_str.strip().split(":")]
        if len(parts) == 2:
            return time(hour=parts[0], minute=parts[1], second=0)
        if len(parts) == 3:
            return time(hour=parts[0], minute=parts[1], second=parts[2])
    except Exception:
        return None
    return None


def _is_time_in_window(current_t: time, start_t: time, end_t: time) -> bool:
    """Check if current_t is within [start_t, end_t], supporting overnight windows."""
    if start_t <= end_t:
        return start_t <= current_t <= end_t
    # Overnight window (e.g. 22:00 to 06:00)
    return current_t >= start_t or current_t <= end_t


def analyze_rapid_reentry_after_loss(
    trades: Sequence[TradeRecord],
    config: BehaviorAnalysisConfig,
) -> tuple[list[BehaviorFinding], list[str]]:
    """Detect trades opened within a configurable time window after a realized loss.

    Strictly requires subsequent trade open_time >= prior trade close_time to avoid
    falsely flagging concurrent, overlapping, or hedging positions.
    """
    findings: list[BehaviorFinding] = []
    limitations: list[str] = []

    if not trades:
        return findings, limitations

    # Ensure trades are deterministically sorted
    sorted_trades = _sort_trades_chronological(trades)
    window_seconds = config.reentry_window_minutes * 60.0

    # Index trades for efficient pairwise lookahead
    for i, prior in enumerate(sorted_trades):
        if prior.net_pnl >= 0.0 or prior.close_time is None:
            continue

        prior_close = _ensure_timezone(prior.close_time)
        if prior_close is None:
            continue

        # Look at subsequent trades opened after this loss closed
        for j in range(i + 1, len(sorted_trades)):
            subsequent = sorted_trades[j]
            subsequent_open = _ensure_timezone(subsequent.open_time)
            if subsequent_open is None:
                continue

            # If subsequent trade opened BEFORE prior trade closed, it was a concurrent position
            if subsequent_open < prior_close:
                continue

            time_gap = (subsequent_open - prior_close).total_seconds()
            if time_gap < 0:
                continue

            # If beyond window, since trades are sorted by close_time (not strictly open_time),
            # we check gap but cannot immediately break for all j; we evaluate up to window
            if time_gap <= window_seconds:
                # Assess severity based on speed and volume escalation
                same_symbol = prior.symbol == subsequent.symbol
                vol_ratio = subsequent.volume / prior.volume if prior.volume > 0.0 else 1.0

                if time_gap <= 300.0 and (vol_ratio >= 1.25 or same_symbol):
                    severity = BehaviorSeverity.HIGH
                elif time_gap <= 600.0 or vol_ratio > 1.0:
                    severity = BehaviorSeverity.MEDIUM
                else:
                    severity = BehaviorSeverity.LOW

                gap_minutes = round(time_gap / 60.0, 2)
                loss_abs = round(abs(prior.net_pnl), 2)

                finding = BehaviorFinding(
                    id=str(uuid.uuid4()),
                    pattern_type=BehaviorPatternType.RAPID_REENTRY_AFTER_LOSS,
                    severity=severity,
                    title=f"Rapid re-entry {gap_minutes}m after loss on {prior.symbol}",
                    description=(
                        f"Trade {subsequent.id} was opened {gap_minutes} minutes after "
                        f"closing a loss of ${loss_abs:.2f} on {prior.symbol}. "
                        f"Subsequent volume: {subsequent.volume} lots (prior: {prior.volume} lots)."
                    ),
                    detected_at=subsequent_open,
                    trade_id=str(subsequent.id),
                    related_trade_ids=[str(prior.id)],
                    evidence={
                        "prior_trade_id": str(prior.id),
                        "prior_symbol": prior.symbol,
                        "prior_close_time": prior_close.isoformat(),
                        "prior_loss_amount": loss_abs,
                        "subsequent_trade_id": str(subsequent.id),
                        "subsequent_symbol": subsequent.symbol,
                        "subsequent_open_time": subsequent_open.isoformat(),
                        "time_gap_seconds": round(time_gap, 1),
                        "time_gap_minutes": gap_minutes,
                        "reentry_window_minutes": config.reentry_window_minutes,
                        "prior_volume": prior.volume,
                        "subsequent_volume": subsequent.volume,
                        "volume_ratio": round(vol_ratio, 2),
                        "volume_increased": subsequent.volume > prior.volume,
                        "same_symbol": same_symbol,
                    },
                    confidence=1.0,
                    limitations=[],
                    recommended_actions=[
                        f"Review execution journal for trade {subsequent.id} to verify if pre-defined entry checklist was fully met.",
                        "Consider setting an automated cooling-off timer following realized losses.",
                    ],
                )
                findings.append(finding)

    return findings, limitations


def analyze_overtrading_frequency(
    trades: Sequence[TradeRecord],
    config: BehaviorAnalysisConfig,
) -> tuple[list[BehaviorFinding], list[str]]:
    """Detect unusually high trading frequency by calendar day and session."""
    findings: list[BehaviorFinding] = []
    limitations: list[str] = []

    if not trades:
        return findings, limitations

    # Determine timezone for day grouping
    tz_str = config.session_timezone or "UTC"
    try:
        group_tz = ZoneInfo(tz_str)
    except Exception:
        group_tz = ZoneInfo("UTC")
        limitations.append(f"Invalid timezone '{tz_str}', fell back to UTC for day grouping.")

    # Group trades by calendar date (using open_time converted to target timezone)
    daily_groups: dict[str, list[TradeRecord]] = defaultdict(list)
    session_groups: dict[tuple[str, str], list[TradeRecord]] = defaultdict(list)

    for t in trades:
        t_open = _ensure_timezone(t.open_time, group_tz)
        if t_open is None:
            continue
        local_open = t_open.astimezone(group_tz)
        date_str = local_open.strftime("%Y-%m-%d")
        daily_groups[date_str].append(t)

        if t.session:
            session_groups[(date_str, t.session.upper())].append(t)

    # 1. Evaluate Daily Frequency Threshold
    daily_counts = [len(records) for records in daily_groups.values()]
    threshold_source = ThresholdSource.DEFAULT_STANDARD
    daily_threshold: int | None = config.max_trades_per_day

    if daily_threshold is not None:
        threshold_source = ThresholdSource.USER_CONFIGURED
    else:
        # Infer baseline from trader's own historical data if >= 5 active days exist
        if len(daily_counts) >= 5:
            arr = np.array(daily_counts, dtype=float)
            mean_c = float(np.mean(arr))
            std_c = float(np.std(arr))
            # Inferred threshold: ceil(mean + 1.5 * std), with a sensible floor of 5
            inferred = int(math.ceil(mean_c + 1.5 * std_c))
            daily_threshold = max(5, inferred)

            threshold_source = ThresholdSource.BASELINE_INFERRED
        else:
            limitations.append(
                f"Insufficient historical trading days ({len(daily_counts)}/5) to infer "
                "a personalized daily frequency baseline. Configure max_trades_per_day explicitly."
            )

    if daily_threshold is not None:
        for date_str, records in sorted(daily_groups.items()):
            count = len(records)
            if count > daily_threshold:
                excess = count - daily_threshold
                severity = (
                    BehaviorSeverity.HIGH
                    if count >= math.ceil(daily_threshold * 1.5)
                    else BehaviorSeverity.MEDIUM
                )

                finding = BehaviorFinding(
                    id=str(uuid.uuid4()),
                    pattern_type=BehaviorPatternType.OVERTRADING_FREQUENCY,
                    severity=severity,
                    title=f"High daily trade frequency: {count} trades on {date_str} (limit: {daily_threshold})",
                    description=(
                        f"Executed {count} trades on {date_str}, exceeding the "
                        f"{threshold_source.value} threshold of {daily_threshold} trades "
                        f"by {excess} trade(s)."
                    ),
                    detected_at=_ensure_timezone(records[-1].open_time, group_tz)
                    or datetime.now(UTC),
                    trade_id=str(records[-1].id),
                    related_trade_ids=[str(r.id) for r in records],
                    evidence={
                        "date": date_str,
                        "trades_count": count,
                        "threshold": daily_threshold,
                        "threshold_source": threshold_source.value,
                        "excess_trades": excess,
                        "timezone": group_tz.key,
                        "trade_ids": [str(r.id) for r in records],
                    },
                    confidence=1.0,
                    limitations=[],
                    recommended_actions=[
                        "Analyze whether late-day trades had lower win rates or expectancy compared to early setups.",
                        "Consider configuring a hard maximum daily trade limit rule.",
                    ],
                )
                findings.append(finding)

    # 2. Evaluate Session Frequency Threshold if configured
    if config.max_trades_per_session is not None:
        session_threshold = config.max_trades_per_session
        for (date_str, s_name), records in sorted(session_groups.items()):
            count = len(records)
            if count > session_threshold:
                severity = (
                    BehaviorSeverity.HIGH
                    if count >= math.ceil(session_threshold * 1.5)
                    else BehaviorSeverity.MEDIUM
                )
                finding = BehaviorFinding(
                    id=str(uuid.uuid4()),
                    pattern_type=BehaviorPatternType.OVERTRADING_FREQUENCY,
                    severity=severity,
                    title=f"High session trade frequency: {count} trades in {s_name} on {date_str}",
                    description=(
                        f"Executed {count} trades during the {s_name} session on {date_str}, "
                        f"exceeding the user-configured session limit of {session_threshold}."
                    ),
                    detected_at=_ensure_timezone(records[-1].open_time, group_tz)
                    or datetime.now(UTC),
                    trade_id=str(records[-1].id),
                    related_trade_ids=[str(r.id) for r in records],
                    evidence={
                        "date": date_str,
                        "session": s_name,
                        "trades_count": count,
                        "session_threshold": session_threshold,
                        "threshold_source": ThresholdSource.USER_CONFIGURED.value,
                        "trade_ids": [str(r.id) for r in records],
                    },
                    confidence=1.0,
                    limitations=[],
                    recommended_actions=[
                        f"Review if setup quality degraded during high-frequency activity in the {s_name} session.",
                    ],
                )
                findings.append(finding)

    return findings, limitations


def analyze_risk_escalation(
    trades: Sequence[TradeRecord],
    config: BehaviorAnalysisConfig,
) -> tuple[list[BehaviorFinding], list[str]]:
    """Analyze position size changes following losses (Martingale-like sizing patterns).

    By default, compares volume within the same symbol to avoid cross-instrument
    contract size distortions.
    """
    findings: list[BehaviorFinding] = []
    limitations: list[str] = []

    if not trades:
        return findings, limitations

    # Group trades based on symbol-normalization setting
    if config.compare_same_symbol_only:
        groups: dict[str, list[TradeRecord]] = defaultdict(list)
        for t in trades:
            groups[t.symbol].append(t)
    else:
        # Cross-symbol analysis
        groups = {"ALL": list(trades)}
        limitations.append(
            "Cross-symbol volume comparison enabled. Contract specifications (e.g. FX vs Gold vs Crypto) "
            "may distort raw lot size comparisons without notional normalization."
        )

    ratio_threshold = config.size_escalation_ratio

    for group_trades in groups.values():
        sorted_trades = _sort_trades_chronological(group_trades)

        for i, prior in enumerate(sorted_trades):
            if prior.net_pnl >= 0.0 or prior.volume <= 0.0:
                continue

            # Look ahead up to size_lookback_trades
            max_lookahead = min(len(sorted_trades), i + 1 + config.size_lookback_trades)
            for j in range(i + 1, max_lookahead):
                subsequent = sorted_trades[j]

                # Ensure subsequent trade opened after or at prior close
                prior_close = _ensure_timezone(prior.close_time)
                subsequent_open = _ensure_timezone(subsequent.open_time)
                if prior_close and subsequent_open and subsequent_open < prior_close:
                    continue

                if subsequent.volume >= (prior.volume * ratio_threshold):
                    multiplier = round(subsequent.volume / prior.volume, 2)
                    severity = (
                        BehaviorSeverity.HIGH if multiplier >= 2.0 else BehaviorSeverity.MEDIUM
                    )

                    loss_abs = round(abs(prior.net_pnl), 2)
                    finding = BehaviorFinding(
                        id=str(uuid.uuid4()),
                        pattern_type=BehaviorPatternType.RISK_ESCALATION,
                        severity=severity,
                        title=f"Position size escalation ({multiplier}x) following loss on {prior.symbol}",
                        description=(
                            f"Statistical sizing pattern: Position size increased from {prior.volume} lots "
                            f"to {subsequent.volume} lots ({multiplier}x) on trade {subsequent.id} "
                            f"following a ${loss_abs:.2f} loss on trade {prior.id}."
                        ),
                        detected_at=subsequent_open or datetime.now(UTC),
                        trade_id=str(subsequent.id),
                        related_trade_ids=[str(prior.id)],
                        evidence={
                            "symbol": prior.symbol,
                            "prior_trade_id": str(prior.id),
                            "prior_volume": prior.volume,
                            "prior_loss_amount": loss_abs,
                            "subsequent_trade_id": str(subsequent.id),
                            "subsequent_volume": subsequent.volume,
                            "size_multiplier": multiplier,
                            "threshold_ratio": ratio_threshold,
                            "same_symbol_comparison": config.compare_same_symbol_only,
                        },
                        confidence=1.0,
                        limitations=[
                            "Statistical sizing pattern observed; does not prove subjective martingale intent.",
                        ],
                        recommended_actions=[
                            "Check if position size escalation conformed to a pre-defined risk model (e.g. percentage of equity) or was discretionary.",
                            "Review trade sizing rules to ensure lot sizes remain consistent regardless of preceding trade outcomes.",
                        ],
                    )
                    findings.append(finding)

    return findings, limitations


def analyze_session_drift(
    trades: Sequence[TradeRecord],
    config: BehaviorAnalysisConfig,
) -> tuple[list[BehaviorFinding], list[str]]:
    """Compare trade entry times with user-defined sessions and hours.

    If no session schedule exists, returns insufficient configuration rather than
    inventing preferred trading hours.
    """
    findings: list[BehaviorFinding] = []
    limitations: list[str] = []

    if not trades:
        return findings, limitations

    has_allowed_sessions = bool(config.allowed_sessions)
    has_time_window = bool(
        config.session_start_time and config.session_end_time and config.session_timezone
    )

    if not has_allowed_sessions and not has_time_window:
        limitations.append(
            "No trading session schedule or allowed hours configured. "
            "The system does not invent preferred trading hours."
        )
        return findings, limitations

    # Parse time window if configured
    start_t = _parse_time_str(config.session_start_time)
    end_t = _parse_time_str(config.session_end_time)
    session_tz: ZoneInfo | None = None

    if has_time_window and start_t and end_t and config.session_timezone:
        try:
            session_tz = ZoneInfo(config.session_timezone)
        except Exception:
            limitations.append(
                f"Invalid session timezone '{config.session_timezone}'. Session hours check skipped."
            )
            has_time_window = False

    allowed_sessions_set = (
        {s.strip().upper() for s in config.allowed_sessions} if config.allowed_sessions else set()
    )

    for trade in trades:
        t_open = _ensure_timezone(trade.open_time)
        if t_open is None:
            continue

        drift_reasons: list[str] = []
        evidence: dict = {
            "trade_id": str(trade.id),
            "symbol": trade.symbol,
            "open_time_utc": t_open.isoformat(),
        }

        # 1. Check allowed sessions tag
        if has_allowed_sessions:
            t_session = (trade.session or "").strip().upper()
            if not t_session or t_session not in allowed_sessions_set:
                drift_reasons.append(
                    f"Session tag '{trade.session or 'NONE'}' not in allowed sessions {sorted(allowed_sessions_set)}"
                )
                evidence["trade_session"] = trade.session
                evidence["allowed_sessions"] = sorted(allowed_sessions_set)

        # 2. Check time window in IANA timezone
        if has_time_window and session_tz and start_t and end_t:
            local_dt = t_open.astimezone(session_tz)
            local_time = local_dt.time()
            if not _is_time_in_window(local_time, start_t, end_t):
                drift_reasons.append(
                    f"Entry time {local_time.strftime('%H:%M:%S')} is outside allowed window "
                    f"[{start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}] in {session_tz.key}"
                )
                evidence["open_time_local"] = local_dt.isoformat()
                evidence["local_time"] = local_time.strftime("%H:%M:%S")
                evidence["allowed_window"] = (
                    f"{start_t.strftime('%H:%M')} - {end_t.strftime('%H:%M')}"
                )
                evidence["timezone"] = session_tz.key

        if drift_reasons:
            finding = BehaviorFinding(
                id=str(uuid.uuid4()),
                pattern_type=BehaviorPatternType.SESSION_DRIFT,
                severity=BehaviorSeverity.LOW
                if len(drift_reasons) == 1
                else BehaviorSeverity.MEDIUM,
                title=f"Session drift: Trade {trade.symbol} entered outside configured hours",
                description="; ".join(drift_reasons),
                detected_at=t_open,
                trade_id=str(trade.id),
                related_trade_ids=[],
                evidence=evidence,
                confidence=1.0,
                limitations=[],
                recommended_actions=[
                    "Verify if out-of-session trading matched an exceptional planned setup or represented schedule drift.",
                    "Review whether trades outside your prime session maintain a positive expectancy.",
                ],
            )
            findings.append(finding)

    return findings, limitations


def calculate_discipline_score(findings: Sequence[BehaviorFinding], total_trades: int) -> float:
    """Calculate deterministic behavioral discipline score (0-100).

    Base score: 100.0. Deducts points based on findings severity.
    """
    if total_trades == 0:
        return 100.0

    score = 100.0
    for f in findings:
        if f.severity == BehaviorSeverity.HIGH:
            score -= 10.0
        elif f.severity == BehaviorSeverity.MEDIUM:
            score -= 5.0
        elif f.severity == BehaviorSeverity.LOW:
            score -= 2.0

    return float(max(0.0, min(100.0, round(score, 1))))


def generate_pattern_summaries(
    findings: Sequence[BehaviorFinding],
) -> list[BehaviorPatternSummary]:
    """Compile aggregated summaries for each behavioral pattern type."""
    type_meta = {
        BehaviorPatternType.RAPID_REENTRY_AFTER_LOSS: "Rapid Re-entry After Loss",
        BehaviorPatternType.OVERTRADING_FREQUENCY: "Overtrading Frequency",
        BehaviorPatternType.RISK_ESCALATION: "Risk Escalation (Martingale-like Sizing)",
        BehaviorPatternType.SESSION_DRIFT: "Session Drift",
    }

    grouped: dict[BehaviorPatternType, list[BehaviorFinding]] = defaultdict(list)
    for f in findings:
        grouped[f.pattern_type].append(f)

    summaries: list[BehaviorPatternSummary] = []
    for p_type, p_name in type_meta.items():
        pattern_findings = grouped[p_type]
        count = len(pattern_findings)

        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
        for f in pattern_findings:
            severity_counts[f.severity.value] += 1

        first_at: datetime | None = None
        last_at: datetime | None = None

        if pattern_findings:
            sorted_by_date = sorted(pattern_findings, key=lambda x: x.detected_at)
            first_at = sorted_by_date[0].detected_at
            last_at = sorted_by_date[-1].detected_at

        if count == 0:
            notes = "No occurrences detected in the analyzed trade history."
        else:
            notes = (
                f"{count} occurrence(s) detected: {severity_counts['HIGH']} high, "
                f"{severity_counts['MEDIUM']} medium, {severity_counts['LOW']} low severity."
            )

        summaries.append(
            BehaviorPatternSummary(
                pattern_type=p_type,
                pattern_name=p_name,
                occurrences_count=count,
                severity_breakdown=severity_counts,
                first_detected_at=first_at,
                last_detected_at=last_at,
                summary_notes=notes,
            )
        )

    return summaries


def analyze_trading_behavior(
    entries: Sequence[JournalEntry | TradeRecord | dict],
    config: BehaviorAnalysisConfig | None = None,
    account_id: uuid.UUID | None = None,
) -> BehaviorSummaryResponse:
    """Execute complete deterministic trading behavior analysis across all patterns."""
    if config is None:
        config = BehaviorAnalysisConfig()

    closed_records, open_count = extract_trade_records(entries)
    total_trades = len(closed_records) + open_count

    all_findings: list[BehaviorFinding] = []
    all_limitations: list[str] = []

    # 1. Rapid Re-entry After Loss
    reentry_findings, reentry_lims = analyze_rapid_reentry_after_loss(
        trades=closed_records,
        config=config,
    )
    all_findings.extend(reentry_findings)
    all_limitations.extend(reentry_lims)

    # 2. Overtrading Frequency (closed records + open records)
    all_trades_for_freq = list(closed_records)
    # Also include any open trade records that have open_time
    for item in entries:
        if isinstance(item, JournalEntry) and item.status != "CLOSED":
            trade_rec = TradeRecord(
                id=str(item.id),
                account_id=str(item.account_id),
                symbol=item.symbol,
                direction=item.direction,
                volume=item.volume,
                entry_price=item.entry_price,
                exit_price=None,
                gross_profit=0.0,
                commission=item.commission or 0.0,
                swap=item.swap or 0.0,
                net_pnl=0.0,
                open_time=item.open_time,
                close_time=item.open_time,
                status=item.status,
                session=item.session,
            )
            all_trades_for_freq.append(trade_rec)

    freq_findings, freq_lims = analyze_overtrading_frequency(
        trades=all_trades_for_freq,
        config=config,
    )
    all_findings.extend(freq_findings)
    all_limitations.extend(freq_lims)

    # 3. Risk Escalation
    escalation_findings, escalation_lims = analyze_risk_escalation(
        trades=closed_records,
        config=config,
    )
    all_findings.extend(escalation_findings)
    all_limitations.extend(escalation_lims)

    # 4. Session Drift
    drift_findings, drift_lims = analyze_session_drift(
        trades=all_trades_for_freq,
        config=config,
    )
    all_findings.extend(drift_findings)
    all_limitations.extend(drift_lims)

    # Sort findings by detected_at descending (most recent first)
    all_findings.sort(key=lambda f: f.detected_at, reverse=True)

    high_c = sum(1 for f in all_findings if f.severity == BehaviorSeverity.HIGH)
    med_c = sum(1 for f in all_findings if f.severity == BehaviorSeverity.MEDIUM)
    low_c = sum(1 for f in all_findings if f.severity == BehaviorSeverity.LOW)

    discipline_score = calculate_discipline_score(all_findings, total_trades)
    pattern_summaries = generate_pattern_summaries(all_findings)

    # Deduplicate general limitations while preserving order
    unique_limitations: list[str] = []
    for lim in all_limitations:
        if lim not in unique_limitations:
            unique_limitations.append(lim)

    return BehaviorSummaryResponse(
        account_id=account_id,
        total_trades_analyzed=total_trades,
        total_findings=len(all_findings),
        high_severity_count=high_c,
        medium_severity_count=med_c,
        low_severity_count=low_c,
        overall_discipline_score=discipline_score,
        pattern_summaries=pattern_summaries,
        findings=all_findings,
        data_limitations=unique_limitations,
        configuration_used=config,
        data_badge=DataClassificationBadge.HISTORICAL_STATISTICS,
    )
