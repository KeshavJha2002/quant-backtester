from __future__ import annotations

from trading_bot.projection_cone import ProjectionConeConfig, analyze_projection_cone
from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
)
from trading_bot.supertrend.strategy import run_supertrend_scans
from trading_bot.tema_macd.strategy import _latest_complete_bar_index

QUALITY_WEIGHT = {
    "D": 0.90,
    "W": 0.85,
}

HOLDING_DAY_PROXY = {
    "D": 70.0,
    "W": 450.0,
}


def _score(freq: str, sigma_move: float, threshold: float) -> float:
    return QUALITY_WEIGHT[freq] * max(0.01, threshold - sigma_move) / HOLDING_DAY_PROXY[freq]


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    threshold = context.min_negative_sigma

    def complete_fetcher(ticker: str, *, type: str):
        data = fetcher(ticker, type=type)
        complete_idx = _latest_complete_bar_index(data["time"].values, type)
        if complete_idx is None or complete_idx <= 0:
            raise ValueError(f"No complete {type} bar available for {ticker}")
        return data.iloc[: complete_idx + 1].reset_index(drop=True)

    content_lines = [
        "## c6_tw",
        f"- Rule: fresh Supertrend buy on the last complete candle and same-timeframe cone sigma `< {threshold}`",
        "- Score:",
        "  - `D: 0.90 * max(0.01, threshold - sigma) / 70`",
        "  - `W: 0.85 * max(0.01, threshold - sigma) / 450`",
        "",
    ]

    for freq in ("D", "W"):
        rows = []
        for segment, tickers in UNIVERSES:
            _, _, recent = run_supertrend_scans(tickers, fetcher, freq, mode="or")
            for ticker in recent[freq]:
                try:
                    result = analyze_projection_cone(
                        ticker,
                        fetch_data_func=complete_fetcher,
                        freq=freq,
                        config=cone_config,
                    )
                    if result["zone"]["sigma_move"] < threshold:
                        rows.append((segment, ticker, result))
                except Exception as exc:
                    print(f"Skipping {ticker}: {exc}")

        rows.sort(key=lambda row: (float(row[2]["zone"]["sigma_move"]), row[1]))
        content_lines.extend(
            [
                f"### {freq}",
                "",
                "| Segment | Ticker | Bar Time | Price | Sigma Move | Score | Price Zone | Anchor Type |",
                "|---|---|---|---:|---:|---:|---|---|",
            ]
        )
        for segment, ticker, result in rows:
            sigma_move = float(result["zone"]["sigma_move"])
            content_lines.append(
                f"| {segment} | `{ticker}` | {result['as_of']} | {result['current_price']:.2f} | "
                f"{sigma_move:.2f} | {_score(freq, sigma_move, threshold):.4f} | {result['zone']['name']} | {result['anchor']['type']} |"
            )
        if not rows:
            content_lines.append("| - | - | - | - | - | - | - | - |")
        content_lines.append("")

    return build_strategy_section(
        "combination",
        6,
        "Combination Strategy c6: Trend Supertrend D+W + Projection Cone",
        "\n".join(content_lines),
    )
