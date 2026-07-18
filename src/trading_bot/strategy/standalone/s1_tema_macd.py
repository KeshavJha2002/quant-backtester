from __future__ import annotations

from trading_bot.strategy.common import (
    StrategyContext,
    build_strategy_section,
    write_section_report,
)
from trading_bot.tema_macd.main import build_tema_macd_report


def build_section(context: StrategyContext):
    from trading_bot.strategy.common import get_fetcher

    report = build_tema_macd_report(
        tight=context.tight,
        fetch_data_func=get_fetcher(context.refresh_data),
    )
    return build_strategy_section("standalone", 1, "Standalone Strategy 1: TEMA MACD", report)


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
