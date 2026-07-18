from __future__ import annotations

from trading_bot.projection_cone import ProjectionConeConfig, analyze_projection_cone
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
    write_section_report,
)
from trading_bot.supertrend.strategy import run_supertrend_scans


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    rows = []
    for segment, tickers in UNIVERSES:
        weekly_bull, _, _ = run_supertrend_scans(tickers, fetcher, "W", mode="or")
        _, _, daily_latest = run_supertrend_scans(tickers, fetcher, "D", mode="pullback")
        weekly_bull_set = set(weekly_bull["W"])
        daily_within_weekly = [ticker for ticker in daily_latest["D"] if ticker in weekly_bull_set]
        for ticker in daily_within_weekly:
            try:
                result = analyze_projection_cone(
                    ticker, fetch_data_func=fetcher, freq="D", config=cone_config
                )
                if result["zone"]["sigma_move"] < 0:
                    rows.append((segment, ticker, result))
            except Exception as exc:
                print(f"Skipping {ticker}: {exc}")
    rows.sort(key=lambda row: (float(row[2]["zone"]["sigma_move"]), row[1]))

    content_lines = [
        "## Trend Supertrend D in W + Projection Cone D",
        "- Rule: daily fresh buy on the last complete candle, weekly bull state already active, and daily cone position in the negative half (`sigma < 0`)",
        "",
        "| Segment | Ticker | Bar Time | Price | Sigma Move | Price Zone | Anchor Type |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for segment, ticker, result in rows:
        content_lines.append(
            f"| {segment} | `{ticker}` | {result['as_of']} | {result['current_price']:.2f} | "
            f"{result['zone']['sigma_move']:.2f} | {result['zone']['name']} | {result['anchor']['type']} |"
        )
    if not rows:
        content_lines.append("| - | - | - | - | - | - | - |")
    return build_strategy_section(
        "combination",
        4,
        "Combination Strategy 4: Trend Supertrend D in W + Projection Cone D",
        "\n".join(content_lines),
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
