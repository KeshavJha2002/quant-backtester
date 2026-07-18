from __future__ import annotations

from trading_bot.mtf.tema_macd import run_tema_macd_mtf_scan
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
    ticker_cell,
    write_section_report,
)
from trading_bot.utility import config


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    rows = []
    for segment, tickers in UNIVERSES:
        daily, _ = run_tema_macd_mtf_scan(tickers, fetcher, config, tight=context.tight)
        rows.append((segment, daily))

    content = "\n".join(
        [
            "## TEMA MACD D in W",
            "| Segment | Count | Tickers |",
            "|---|---:|---|",
            *[f"| {segment} | {len(values)} | {ticker_cell(values)} |" for segment, values in rows],
        ]
    )
    return build_strategy_section(
        "combination", 1, "Combination Strategy 1: TEMA MACD D in W", content
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
