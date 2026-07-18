from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from research.support.cone_backtest import entry_sigma_move, sigma_bucket
from trading_bot.projection_cone import ProjectionConeConfig
from trading_bot.utility import get_fetch_data, nifty50_ns, nifty150_ns, nifty250_ns


def build_observations(
    data, ticker: str, segment: str, freq: str, forward_bars: int, cone_config: ProjectionConeConfig
) -> list[dict[str, float | str]]:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()
    observations: list[dict[str, float | str]] = []
    min_bars = max(cone_config.vol_length + 1, (2 * cone_config.pivot_len) + 1)

    for i in range(min_bars, len(close) - forward_bars):
        sigma_move = entry_sigma_move(close, high, low, i, freq, cone_config)
        if sigma_move is None:
            continue
        observations.append(
            {
                "ticker": ticker,
                "segment": segment,
                "timeframe": freq,
                "sigma_bucket": sigma_bucket(sigma_move),
                "sigma_move": sigma_move,
                "forward_return_pct": (float(close[i + forward_bars]) / float(close[i]) - 1.0)
                * 100.0,
            }
        )
    return observations


def summarize_observations(
    observations: list[dict[str, float | str]],
) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in observations:
        grouped[(str(row["timeframe"]), str(row["segment"]), str(row["sigma_bucket"]))].append(
            float(row["forward_return_pct"])
        )

    summary: list[dict[str, float | str]] = []
    for (timeframe, segment, bucket), returns in sorted(grouped.items()):
        wins = [value for value in returns if value > 0]
        summary.append(
            {
                "timeframe": timeframe,
                "segment": segment,
                "bucket": bucket,
                "sample_count": len(returns),
                "avg_forward_return_pct": sum(returns) / len(returns),
                "win_rate_pct": len(wins) / len(returns) * 100.0,
            }
        )
    return summary


def build_report(
    summary_rows: list[dict[str, float | str]], *, forward_bars_d: int, forward_bars_w: int
) -> str:
    lines = [
        "# Projection Cone Forward Return Study",
        "",
        "This is an observational cone study, not a mechanical entry-exit backtest.",
        f"- Daily forward window: `{forward_bars_d}` bars",
        f"- Weekly forward window: `{forward_bars_w}` bars",
        "",
        "| Timeframe | Segment | Cone Bucket | Samples | Avg Forward Return % | Win Rate % |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['timeframe']} | {row['segment']} | {row['bucket']} | {row['sample_count']} | "
            f"{row['avg_forward_return_pct']:.2f} | {row['win_rate_pct']:.2f} |"
        )
    if not summary_rows:
        lines.append("| - | - | - | - | - | - |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--forward-bars-d", type=int, default=20)
    parser.add_argument("--forward-bars-w", type=int, default=8)
    args = parser.parse_args()

    fetch_data_func = get_fetch_data(refresh=args.refresh_data)
    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    observations: list[dict[str, float | str]] = []

    for freq, forward_bars in (("D", args.forward_bars_d), ("W", args.forward_bars_w)):
        print(f"\nProjection Cone {freq} forward study")
        for segment, tickers in universes.items():
            count_before = len(observations)
            for ticker in tickers:
                try:
                    data = fetch_data_func(ticker, type=freq)
                    observations.extend(
                        build_observations(data, ticker, segment, freq, forward_bars, cone_config)
                    )
                except Exception as exc:
                    print(f"Skipping {ticker} {freq}: {exc}")
            print(f"{segment} samples={len(observations) - count_before}")

    summary_rows = summarize_observations(observations)
    report = build_report(
        summary_rows, forward_bars_d=args.forward_bars_d, forward_bars_w=args.forward_bars_w
    )
    output_path = Path("results") / "projection_cone.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
