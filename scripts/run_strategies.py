from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.strategy.registry import run_strategies

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["standalone", "combination"])
    parser.add_argument("--strategy", required=True, nargs="+")
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--tight", action="store_true")
    parser.add_argument("--min-negative-sigma", type=float, default=-1.0)
    args = parser.parse_args()
    strategies: list[int] = []
    for raw_value in args.strategy:
        strategies.extend(int(part.strip()) for part in raw_value.split(",") if part.strip())
    print(
        run_strategies(
            mode=args.mode,
            strategies=strategies,
            refresh_data=args.refresh_data,
            tight=args.tight,
            min_negative_sigma=args.min_negative_sigma,
        )
    )
