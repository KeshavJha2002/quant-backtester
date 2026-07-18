from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

from research.support.cone_backtest import append_trade, entry_sigma_move, sigma_bucket
from trading_bot.projection_cone import ProjectionConeConfig
from trading_bot.utility import (
    compute_st_trend_from_config,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


def backtest_supertrend_weekly_with_cone(
    data: pd.DataFrame, cone_config: ProjectionConeConfig
) -> list[dict[str, float]]:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()
    time_values = pd.to_datetime(data["time"].values)

    trend1 = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend2 = compute_st_trend_from_config(close, high, low, 14, 3.0, 2)
    trend3 = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)

    trades: list[dict[str, float]] = []
    in_position = False
    entry_price = 0.0
    entry_time = None
    entry_sigma = 0.0
    entry_bucket = ""

    for i in range(1, len(close)):
        bullish_flip = (
            (trend1[i - 1] == -1 and trend1[i] == 1)
            or (trend2[i - 1] == -1 and trend2[i] == 1)
            or (trend3[i - 1] == -1 and trend3[i] == 1)
        )
        all_bearish = trend1[i] == -1 and trend2[i] == -1 and trend3[i] == -1

        if not in_position and bullish_flip:
            sigma_move = entry_sigma_move(close, high, low, i, "W", cone_config)
            if sigma_move is None:
                continue
            in_position = True
            entry_price = float(close[i])
            entry_time = time_values[i]
            entry_sigma = float(sigma_move)
            entry_bucket = sigma_bucket(float(sigma_move))
            continue

        if in_position and all_bearish:
            append_trade(
                trades,
                entry_price=entry_price,
                exit_price=float(close[i]),
                entry_time=entry_time,
                exit_time=time_values[i],
                sigma_move=entry_sigma,
                sigma_bucket_value=entry_bucket,
            )
            in_position = False

    return trades


def summarize_by_segment(
    all_trades: dict[str, list[dict[str, float]]],
) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    for segment, trades in all_trades.items():
        grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
        for trade in trades:
            grouped[str(trade["sigma_bucket"])].append(trade)
        for bucket, bucket_trades in sorted(grouped.items()):
            returns = [trade["return_pct"] for trade in bucket_trades]
            durations = [trade["duration_days"] for trade in bucket_trades]
            wins = [value for value in returns if value > 0]
            rows.append(
                {
                    "segment": segment,
                    "bucket": bucket,
                    "trade_count": len(bucket_trades),
                    "avg_return_pct": sum(returns) / len(returns),
                    "win_rate_pct": len(wins) / len(returns) * 100.0,
                    "median_duration_days": median(durations),
                }
            )
    return rows


def build_report(summary_rows: list[dict[str, float | str]]) -> str:
    lines = [
        "# Trend Supertrend W with Projection Cone W",
        "",
        "| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['segment']} | {row['bucket']} | {row['trade_count']} | {row['avg_return_pct']:.2f} | "
            f"{row['win_rate_pct']:.2f} | {row['median_duration_days']:.2f} |"
        )
    if not summary_rows:
        lines.append("| - | - | - | - | - | - |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()

    fetch_data_func = get_fetch_data(refresh=args.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    all_trades: dict[str, list[dict[str, float]]] = {segment: [] for segment in universes}

    print("\nTesting Trend Supertrend W + Projection Cone W")
    for segment, tickers in universes.items():
        for ticker in tickers:
            try:
                data = fetch_data_func(ticker, type="W")
                all_trades[segment].extend(backtest_supertrend_weekly_with_cone(data, cone_config))
            except Exception as exc:
                print(f"Skipping {ticker}: {exc}")
        print(f"{segment} trades={len(all_trades[segment])}")

    report = build_report(summarize_by_segment(all_trades))
    output_path = Path("results") / "trend_supertrend_w_projection_cone.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
