"""Standalone diagnostic verification script for MetaTrader 5 Windows terminal IPC.

Validates read-only connectivity, terminal status, account metadata, and historical
deal retrieval. Never logs passwords or sensitive credentials.
Returns non-zero exit code on failure.
"""

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Ensure backend directory is in sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.config import settings  # noqa: E402
from app.core.errors import (  # noqa: E402
    MT5AccountError,
    MT5InitializationError,
    MT5QueryError,
)
from app.services.mt5_connector import MT5Connector  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify read-only MetaTrader 5 Windows IPC connection."
    )
    parser.add_argument(
        "--path",
        type=str,
        default=settings.MT5_TERMINAL_PATH,
        help="Path to MT5 terminal64.exe (default: from configuration)",
    )
    parser.add_argument(
        "--login",
        type=int,
        default=int(os.environ.get("MT5_LOGIN", 0)) if os.environ.get("MT5_LOGIN") else None,
        help="Trading account login identifier (or set MT5_LOGIN env var)",
    )
    parser.add_argument(
        "--server",
        type=str,
        default=os.environ.get("MT5_SERVER"),
        help="Broker server name (or set MT5_SERVER env var)",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=os.environ.get("MT5_PASSWORD"),
        help="Investor/trading password (preferred: MT5_PASSWORD env var; never logged)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of historical days of deals to query (default: 30)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=settings.MT5_TIMEOUT_SECONDS * 1000,
        help="Timeout in milliseconds for terminal connection",
    )
    return parser.parse_args()


def run_verification() -> int:
    args = parse_args()

    print("=" * 70)
    print("MetaTrader 5 Windows Terminal IPC Verification (TASK-005 POC)")
    print("=" * 70)
    print(f"[*] Target Terminal Path: {args.path}")
    print(f"[*] Python Architecture : {sys.version.split()[0]} ({sys.platform})")

    # Step 1: Verify physical terminal binary presence
    target_path = Path(args.path)
    if not target_path.exists():
        print(f"[!] ERROR: Terminal executable not found at '{args.path}'")
        return 1
    print(f"[+] Verified terminal binary exists: {target_path.stat().st_size:,} bytes")

    connector = MT5Connector(terminal_path=str(target_path))

    try:
        # Step 2: Initialize connection
        print("[*] Initializing MT5 IPC connection...")
        try:
            connector.initialize(
                path=str(target_path),
                login=args.login,
                password=args.password,
                server=args.server,
                timeout=args.timeout,
            )
            print("[+] MT5 IPC initialization succeeded!")
        except MT5InitializationError as e:
            print(f"[!] Terminal initialization failed: {e.message}")
            if e.details:
                print(f"    Details: {e.details}")
            print("\n[NOTE] If this terminal has no active account configured, pass")
            print("       --login, --server, and --password (or env vars) to authenticate,")
            print("       or launch MT5 once to log into your broker demo account.")
            return 2

        # Step 3: Terminal Status
        print("\n[*] Inspecting Terminal Status:")
        try:
            term_status = connector.get_terminal_status()
            print(f"    - Connected to Server : {term_status.connected}")
            print(f"    - Build Number        : {term_status.build}")
            print(f"    - Terminal Name       : {term_status.name}")
            print(f"    - Company / Broker    : {term_status.company or 'N/A'}")
            print(f"    - Ping Latency        : {term_status.ping_last} µs")
            print(f"    - Trading Allowed     : {term_status.trade_allowed}")
        except MT5QueryError as e:
            print(f"[!] Failed to read terminal status: {e.message}")
            return 3

        # Step 4: Account Information
        print("\n[*] Inspecting Account Information:")
        account_connected = False
        try:
            acc_info = connector.get_account_info()
            account_connected = True
            print(f"    - Masked Login        : {acc_info.masked_login}")
            print(f"    - Server Name         : {acc_info.server}")
            print(f"    - Account Type        : {acc_info.trade_mode_name} ({acc_info.trade_mode})")
            print(f"    - Base Currency       : {acc_info.currency}")
            print(f"    - Leverage            : 1:{acc_info.leverage}")
            print(f"    - Balance             : {acc_info.balance:,.2f} {acc_info.currency}")
            print(f"    - Equity              : {acc_info.equity:,.2f} {acc_info.currency}")
            print(f"    - Floating P&L        : {acc_info.profit:,.2f} {acc_info.currency}")
            print(f"    - Free Margin         : {acc_info.margin_free:,.2f} {acc_info.currency}")
        except MT5AccountError as e:
            print(f"[!] Could not retrieve account info: {e.message}")
            print(
                "    [Info] Terminal is initialized but not authorized with an active broker account."
            )

        # Step 5: Read Historical Deals (Bounded Date Range)
        if account_connected:
            print(f"\n[*] Querying Historical Deals (Past {args.days} Days):")
            date_to = datetime.now(UTC)
            date_from = date_to - timedelta(days=args.days)
            try:
                deals = connector.get_historical_deals(date_from=date_from, date_to=date_to)
                print(f"[+] Total Deals Retrieved: {len(deals)}")

                if deals:
                    sample_size = min(3, len(deals))
                    print(f"    Displaying {sample_size} sanitized sample deal(s):")
                    for idx, d in enumerate(deals[:sample_size], start=1):
                        entry_name = {0: "IN", 1: "OUT", 2: "INOUT", 3: "OUT_BY"}.get(
                            d.entry, str(d.entry)
                        )
                        type_name = {0: "BUY", 1: "SELL", 2: "BALANCE"}.get(d.type, str(d.type))
                        print(
                            f"    [{idx}] Ticket: {d.ticket} | Time: {d.time.strftime('%Y-%m-%d %H:%M:%S')} | "
                            f"{type_name} {entry_name} | {d.symbol} | Vol: {d.volume:.2f} | "
                            f"Price: {d.price:.5f} | Net P&L: {d.profit:+.2f}"
                        )
                else:
                    print("    (No historical deals found in the specified date range)")
            except MT5QueryError as e:
                print(f"[!] Historical deal query failed: {e.message}")
                return 4

            # Step 6: Diagnostic Open Positions
            print("\n[*] Querying Active Positions (Diagnostic Only):")
            try:
                positions = connector.get_open_positions()
                print(f"[+] Open Positions Count: {len(positions)}")
                if positions:
                    for idx, p in enumerate(positions[:3], start=1):
                        pos_type = "BUY" if p.type == 0 else "SELL"
                        print(
                            f"    [{idx}] Ticket: {p.ticket} | {pos_type} {p.symbol} | "
                            f"Vol: {p.volume:.2f} | Open: {p.price_open:.5f} | Float P&L: {p.profit:+.2f}"
                        )
            except MT5QueryError as e:
                print(f"[!] Open positions query failed: {e.message}")
                return 5

        print("\n" + "=" * 70)
        print("[+] MetaTrader 5 Read-Only IPC Verification completed successfully.")
        print("=" * 70)
        return 0

    finally:
        print("[*] Releasing MT5 IPC connection and shutting down...")
        connector.shutdown()
        print("[+] MT5 shutdown complete.")


if __name__ == "__main__":
    sys.exit(run_verification())
