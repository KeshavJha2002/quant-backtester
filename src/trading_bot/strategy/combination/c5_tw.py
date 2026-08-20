from __future__ import annotations

from trading_bot.projection_cone import ProjectionConeConfig, analyze_projection_cone
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_complete_bar_fetcher,
    get_fetcher,
)
from trading_bot.tema_macd.strategy import tema_macd_fresh_bull_screen
from trading_bot.utility import config

QUALITY_WEIGHT = 0.95
HOLDING_DAY_PROXY = 98.0


def _score(sigma_move: float, threshold: float) -> float:
    return QUALITY_WEIGHT * max(0.01, threshold - sigma_move) / HOLDING_DAY_PROXY


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    complete_fetcher = get_complete_bar_fetcher(fetcher)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    threshold = context.min_negative_sigma

    rows = []
    for segment, tickers in UNIVERSES:
        weekly = tema_macd_fresh_bull_screen(tickers, fetcher, "W", config)
        for ticker in weekly:
            try:
                result = analyze_projection_cone(
                    ticker,
                    fetch_data_func=complete_fetcher,
                    freq="W",
                    config=cone_config,
                )
                if result["zone"]["sigma_move"] < threshold:
                    rows.append((segment, ticker, result))
            except Exception as exc:
                print(f"Skipping {ticker}: {exc}")

    rows.sort(key=lambda row: (float(row[2]["zone"]["sigma_move"]), row[1]))
    lines = [
        "## c5_tw",
        f"- Rule: weekly fresh TEMA MACD buy on the last complete candle and weekly cone sigma `< {threshold}`",
        "- Score: `0.95 * max(0.01, threshold - sigma) / 98`",
        "",
        "| Segment | Ticker | Bar Time | Price | Sigma Move | Score | Price Zone | Anchor Type |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for segment, ticker, result in rows:
        sigma_move = float(result["zone"]["sigma_move"])
        lines.append(
            f"| {segment} | `{ticker}` | {result['as_of']} | {result['current_price']:.2f} | "
            f"{sigma_move:.2f} | {_score(sigma_move, threshold):.4f} | {result['zone']['name']} | {result['anchor']['type']} |"
        )
    if not rows:
        lines.append("| - | - | - | - | - | - | - | - |")

    return build_strategy_section(
        "combination",
        5,
        "Combination Strategy c5: TEMA MACD W + Projection Cone W",
        "\n".join(lines),
    )
