"""Compatibility shim for backend.analytics."""

from app.analytics.engine import (
    TradeRecord,
    calculate_breakdowns,
    calculate_equity_curve,
    calculate_performance_metrics,
    calculate_sharpe_sortino,
    extract_trade_records,
)

__all__ = [
    "TradeRecord",
    "extract_trade_records",
    "calculate_performance_metrics",
    "calculate_equity_curve",
    "calculate_sharpe_sortino",
    "calculate_breakdowns",
]
