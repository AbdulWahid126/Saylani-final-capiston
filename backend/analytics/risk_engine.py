"""Compatibility shim for backend.analytics.risk_engine."""

from app.analytics.risk_engine import (
    BUILTIN_TEMPLATES,
    TEMPLATE_1STEP_TRAILING_50K,
    TEMPLATE_2STEP_100K,
    TEMPLATE_STATIC_10K,
    evaluate_account_risk,
    get_builtin_template,
    get_daily_reset_window,
)

__all__ = [
    "TEMPLATE_2STEP_100K",
    "TEMPLATE_1STEP_TRAILING_50K",
    "TEMPLATE_STATIC_10K",
    "BUILTIN_TEMPLATES",
    "get_builtin_template",
    "get_daily_reset_window",
    "evaluate_account_risk",
]
