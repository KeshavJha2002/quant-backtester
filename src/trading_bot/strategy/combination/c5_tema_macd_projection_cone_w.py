from __future__ import annotations

from trading_bot.projection_cone import ProjectionConeConfig, analyze_projection_cone
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
    write_section_report,
)
from trading_bot.tema_macd.strategy import _latest_complete_bar_index, tema_macd_fresh_bull_screen
from trading_bot.utility import config


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
        weekly = tema_macd_fresh_bull_screen(tickers, fetcher, "W", config)
        for ticker in weekly:
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
        "## TEMA MACD W + Projection Cone W",
        "- Rule: weekly fresh buy on the last complete candle and weekly cone position in the negative half (`sigma < 0`)",
        "",
        "| Segment | Ticker | Bar Time | Price | Sigma Move | Sigma Bucket | Price Zone | Anchor Type |",
        "|---|---|---|---:|---:|---|---|---|",
    ]
    for segment, ticker, result in rows:
        sigma_move = result["zone"]["sigma_move"]
        sigma_bucket = "Negative Half"
        content_lines.append(
            f"| {segment} | `{ticker}` | {result['as_of']} | {result['current_price']:.2f} | "
            f"{sigma_move:.2f} | {sigma_bucket} | {result['zone']['name']} | {result['anchor']['type']} |"
        )
    if not rows:
        content_lines.append("| - | - | - | - | - | - | - | - |")
    return build_strategy_section(
        "combination",
        5,
        "Combination Strategy 5: TEMA MACD W + Projection Cone W",
        "\n".join(content_lines),
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
