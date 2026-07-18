from __future__ import annotations

from trading_bot.strategy.common import (
    StrategyContext,
    build_strategy_section,
    write_section_report,
)
from trading_bot.supertrend.main import build_supertrend_report


def build_section(context: StrategyContext):
    from trading_bot.strategy.common import get_fetcher

    report = build_supertrend_report(fetch_data_func=get_fetcher(context.refresh_data))
    return build_strategy_section(
        "standalone", 2, "Standalone Strategy 2: Trend Supertrend", report
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
