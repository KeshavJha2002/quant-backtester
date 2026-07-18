from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from trading_bot.strategy.combination.c5_tw import build_section as build_c5_tw
from trading_bot.strategy.combination.c6_tw import build_section as build_c6_tw
from trading_bot.strategy.common import StrategyContext, render_combined_report
from trading_bot.utility import ensure_output_dir

COMBINATION_BUILDERS = {
    "c5": build_c5_tw,
    "c6": build_c6_tw,
}


def _report_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _report_filename(mode: str, strategies: list[str]) -> str:
    ordered = sorted(dict.fromkeys(strategies))
    return f"{mode}_{'_'.join(ordered)}.md"


def run_strategies(
    *,
    mode: str,
    strategies: list[str],
    refresh_data: bool = False,
    cone_threshold: float = 1.0,
) -> str:
    if mode != "combination":
        raise ValueError("run_tw_combinations.py currently supports only mode=combination")

    context = StrategyContext(
        refresh_data=refresh_data,
        tight=False,
        min_negative_sigma=cone_threshold,
    )

    builders = COMBINATION_BUILDERS
    ordered = sorted(dict.fromkeys(strategy.lower() for strategy in strategies))
    sections = []
    for strategy in ordered:
        builder = builders.get(strategy)
        if builder is None:
            raise ValueError(f"Unknown strategy token {strategy}. Use c5 and/or c6.")
        sections.append(builder(context))

    output_dir = ensure_output_dir("report", _report_date())
    output_path = output_dir / _report_filename(mode, ordered)
    output_path.write_text(render_combined_report(sections), encoding="utf-8")
    return str(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["combination"])
    parser.add_argument("--strategy", required=True, nargs="+")
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--cone-threshold", type=float, default=1.0)
    args = parser.parse_args()

    strategies: list[str] = []
    for raw_value in args.strategy:
        strategies.extend(part.strip() for part in raw_value.split(",") if part.strip())

    print(
        run_strategies(
            mode=args.mode,
            strategies=strategies,
            refresh_data=args.refresh_data,
            cone_threshold=args.cone_threshold,
        )
    )
