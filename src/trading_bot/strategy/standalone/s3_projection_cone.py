from __future__ import annotations

from trading_bot.strategy.common import (
    UNIVERSES,
    StrategyContext,
    build_strategy_section,
    get_fetcher,
    scan_projection_cone_latest,
    write_section_report,
)


def build_section(context: StrategyContext):
    fetcher = get_fetcher(context.refresh_data)
    sections = []
    for freq in ("D", "W"):
        rows = []
        for segment, tickers in UNIVERSES:
            rows.extend(scan_projection_cone_latest(tickers, fetcher, segment=segment, freq=freq))
        rows.sort(key=lambda row: (float(row["sigma_move"]), str(row["ticker"])))
        sections.extend(
            [
                f"## {freq} Projection Cone",
                "",
                "| Segment | Ticker | Bar Time | Price | Sigma Move | Sigma Bucket | Price Zone | Anchor Type | Anchor Price |",
                "|---|---|---|---:|---:|---|---|---|---:|",
            ]
        )
        for row in rows:
            sections.append(
                f"| {row['segment']} | `{row['ticker']}` | {row['bar_time']} | "
                f"{row['current_price']:.2f} | {row['sigma_move']:.2f} | {row['sigma_bucket']} | "
                f"{row['price_zone']} | {row['anchor_type']} | {row['anchor_price']:.2f} |"
            )
        if not rows:
            sections.append("| - | - | - | - | - | - | - | - | - |")
        sections.append("")
    return build_strategy_section(
        "standalone",
        3,
        "Standalone Strategy 3: Projection Cone",
        "\n".join(sections),
    )


def run(context: StrategyContext) -> str:
    return write_section_report(build_section(context))
