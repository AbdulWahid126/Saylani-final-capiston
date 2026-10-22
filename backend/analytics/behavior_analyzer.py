"""Compatibility shim for backend.analytics.behavior_analyzer."""

from app.analytics.behavior_analyzer import (
    analyze_overtrading_frequency,
    analyze_rapid_reentry_after_loss,
    analyze_risk_escalation,
    analyze_session_drift,
    analyze_trading_behavior,
    calculate_discipline_score,
    generate_pattern_summaries,
)

__all__ = [
    "analyze_rapid_reentry_after_loss",
    "analyze_overtrading_frequency",
    "analyze_risk_escalation",
    "analyze_session_drift",
    "calculate_discipline_score",
    "generate_pattern_summaries",
    "analyze_trading_behavior",
]
