"""Shim providing backward-compatible service imports."""

from app.services.mt5_connector import MT5Connector

__all__ = ["MT5Connector"]
