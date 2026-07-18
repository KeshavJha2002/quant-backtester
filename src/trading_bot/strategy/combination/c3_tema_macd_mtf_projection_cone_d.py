from __future__ import annotations

from trading_bot.mtf.tema_macd_projection_cone import (
    build_markdown_report,
    scan_tema_macd_projection_cone,
)
from trading_bot.projection_cone import ProjectionConeConfig
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
    write_section_report,
)
from trading_bot.utility import config


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    matches = []
    for segment, tickers in UNIVERSES:
        matches.extend(
            scan_tema_macd_projection_cone(
                tickers,
                fetcher,
                segment=segment,
                tema_config=config,
                cone_config=cone_config,
                min_negative_sigma=0.0,
            )
        )
    content = build_markdown_report(matches, min_negative_sigma=0.0)
    return build_strategy_section(
        "combination",
        3,
        "Combination Strategy 3: TEMA MACD D in W + Projection Cone D",
        content,
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
