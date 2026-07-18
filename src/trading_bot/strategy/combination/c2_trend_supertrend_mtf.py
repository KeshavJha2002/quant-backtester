from __future__ import annotations

from trading_bot.mtf.supertrend import run_supertrend_mtf_scan
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
    ticker_cell,
    write_section_report,
)


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    rows = []
    for segment, tickers in UNIVERSES:
        daily, _ = run_supertrend_mtf_scan(tickers, fetcher)
        rows.append((segment, daily))

    content = "\n".join(
        [
            "## Trend Supertrend D in W",
            "| Segment | Count | Tickers |",
            "|---|---:|---|",
            *[f"| {segment} | {len(values)} | {ticker_cell(values)} |" for segment, values in rows],
        ]
    )
    return build_strategy_section(
        "combination", 2, "Combination Strategy 2: Trend Supertrend D in W", content
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
