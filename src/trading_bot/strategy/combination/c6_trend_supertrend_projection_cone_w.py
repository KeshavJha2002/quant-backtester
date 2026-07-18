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
from trading_bot.tema_macd.strategy import _latest_complete_bar_index


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)

    def complete_weekly_fetcher(ticker: str, *, type: str):
        data = fetcher(ticker, type=type)
        complete_idx = _latest_complete_bar_index(data["time"].values, type)
        if complete_idx is None or complete_idx <= 0:
            raise ValueError(f"No complete {type} bar available for {ticker}")
        return data.iloc[: complete_idx + 1].reset_index(drop=True)

    rows = []
    for segment, tickers in UNIVERSES:
        _, _, weekly_recent = run_supertrend_scans(tickers, fetcher, "W", mode="or")
        for ticker in weekly_recent["W"]:
            try:
                result = analyze_projection_cone(
                    ticker,
                    fetch_data_func=complete_weekly_fetcher,
                    freq="W",
                    config=cone_config,
                )
                if result["zone"]["sigma_move"] < 0:
                    rows.append((segment, ticker, result))
            except Exception as exc:
                print(f"Skipping {ticker}: {exc}")
    rows.sort(key=lambda row: (float(row[2]["zone"]["sigma_move"]), row[1]))

    content_lines = [
        "## Trend Supertrend W + Projection Cone W",
        "- Rule: weekly fresh buy on the last complete candle and weekly cone position in the negative half (`sigma < 0`)",
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
        6,
        "Combination Strategy 6: Trend Supertrend W + Projection Cone W",
        "\n".join(content_lines),
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
