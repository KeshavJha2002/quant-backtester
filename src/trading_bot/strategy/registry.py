from __future__ import annotations

from datetime import datetime

from trading_bot.strategy.combination import (
    build_c1,
    build_c2,
    build_c3,
    build_c4,
    build_c5,
    build_c6,
    build_c7,
    run_c1,
    run_c2,
    run_c3,
    run_c4,
    run_c5,
    run_c6,
    run_c7,
)
from trading_bot.strategy.common import (
    StrategyContext,
    build_combined_report_filename,
    render_combined_report,
)
from trading_bot.strategy.standalone import build_s1, build_s2, build_s3, run_s1, run_s2, run_s3
from trading_bot.utility import ensure_output_dir

STANDALONE_REGISTRY = {
    1: run_s1,
    2: run_s2,
    3: run_s3,
}

COMBINATION_REGISTRY = {
    1: run_c1,
    2: run_c2,
    3: run_c3,
    4: run_c4,
    5: run_c5,
    6: run_c6,
    7: run_c7,
}

STANDALONE_BUILDERS = {
    1: build_s1,
    2: build_s2,
    3: build_s3,
}

COMBINATION_BUILDERS = {
    1: build_c1,
    2: build_c2,
    3: build_c3,
    4: build_c4,
    5: build_c5,
    6: build_c6,
    7: build_c7,
}


def run_strategy(
    *,
    mode: str,
    strategy: int,
    refresh_data: bool = False,
    tight: bool = False,
    min_negative_sigma: float = -1.0,
) -> str:
    context = StrategyContext(
        refresh_data=refresh_data,
        tight=tight,
        min_negative_sigma=min_negative_sigma,
    )

    if mode == "standalone":
        runner = STANDALONE_REGISTRY.get(strategy)
    elif mode == "combination":
        runner = COMBINATION_REGISTRY.get(strategy)
    else:
        raise ValueError("mode must be 'standalone' or 'combination'")

    if runner is None:
        raise ValueError(f"Unknown strategy number {strategy} for mode {mode}")

    return runner(context)


def run_strategies(
    *,
    mode: str,
    strategies: list[int],
    refresh_data: bool = False,
    tight: bool = False,
    min_negative_sigma: float = -1.0,
) -> str:
    context = StrategyContext(
        refresh_data=refresh_data,
        tight=tight,
        min_negative_sigma=min_negative_sigma,
    )

    ordered_strategies = sorted(dict.fromkeys(strategies))
    builders = _get_builders(mode)
    sections = []
    for strategy_number in ordered_strategies:
        builder = builders.get(strategy_number)
        if builder is None:
            raise ValueError(f"Unknown strategy number {strategy_number} for mode {mode}")
        sections.append(builder(context))

    output_dir = ensure_output_dir("report", _report_date())
    output_path = output_dir / build_combined_report_filename(mode, ordered_strategies)
    output_path.write_text(render_combined_report(sections), encoding="utf-8")
    return str(output_path)


def _get_builders(mode: str):
    if mode == "standalone":
        return STANDALONE_BUILDERS
    if mode == "combination":
        return COMBINATION_BUILDERS
    raise ValueError("mode must be 'standalone' or 'combination'")


def _report_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")
