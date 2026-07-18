from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_bot.monitor.common import build_ticker_strategy_snapshot, format_snapshot_markdown


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", required=True, help="Ticker symbol, with or without .NS")
    args = parser.parse_args()

    snapshot = build_ticker_strategy_snapshot(args.ticker)
    print(format_snapshot_markdown(snapshot))


if __name__ == "__main__":
    main()
