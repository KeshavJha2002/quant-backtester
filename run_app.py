#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def launch_tui() -> None:
    """Launch the interactive Terminal User Interface (TUI)."""
    cmd = [
        str(ROOT / ".venv" / "bin" / "python"),
        str(ROOT / "tui_app.py"),
    ]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nTerminal closed.")


def launch_web_app(port: int = 8501) -> None:
    """Launch the Streamlit web dashboard if requested."""
    print(f"\n⚡ Launching Web Dashboard on http://localhost:{port} ...")
    cmd = [
        str(ROOT / ".venv" / "bin" / "streamlit"),
        "run",
        str(ROOT / "app.py"),
        f"--server.port={port}",
        "--server.headless=false",
    ]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


def launch_cli_scanner(refresh: bool, universe: str) -> None:
    """Run instant CLI scanner report."""
    cmd = [
        str(ROOT / ".venv" / "bin" / "python"),
        str(ROOT / "scripts" / "scan_daily_champions.py"),
        f"--universe={universe}",
    ]
    if refresh:
        cmd.append("--refresh")
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantum Trading & Portfolio Decision Terminal")
    parser.add_argument("--web", action="store_true", help="Launch Streamlit Web UI instead of TUI")
    parser.add_argument("--cli", action="store_true", help="Run instant text report without interactive UI")
    parser.add_argument("--refresh", action="store_true", help="Refresh live market data (in CLI mode)")
    parser.add_argument("--universe", default="all", choices=["all", "N150", "N250", "N50"], help="Target universe for CLI mode")
    parser.add_argument("--port", type=int, default=8501, help="Port for Web UI (default 8501)")
    args = parser.parse_args()

    if args.cli:
        launch_cli_scanner(args.refresh, args.universe)
    elif args.web:
        launch_web_app(args.port)
    else:
        launch_tui()


if __name__ == "__main__":
    main()
