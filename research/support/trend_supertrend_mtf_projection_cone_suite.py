from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

from research.support.cone_backtest import append_trade, entry_sigma_move, sigma_bucket
from research.support.selection import (
    apply_safe_slice,
    parse_range_arg,
    parse_universe_arg,
    slice_label,
    update_slice_report,
)
from trading_bot.projection_cone import ProjectionConeConfig
from trading_bot.utility import (
    compute_st_trend_from_config,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


def backtest_supertrend_mtf_negative_cone(
    daily_data: pd.DataFrame,
    weekly_data: pd.DataFrame,
    cone_config: ProjectionConeConfig,
    min_negative_sigma: float,
) -> list[dict[str, float]]:
    daily_close = np.asarray(daily_data["close"].values, float).ravel()
    daily_high = np.asarray(daily_data["high"].values, float).ravel()
    daily_low = np.asarray(daily_data["low"].values, float).ravel()
    daily_time = pd.to_datetime(daily_data["time"].values)
    weekly_close = np.asarray(weekly_data["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_data["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_data["low"].values, float).ravel()
    weekly_time = pd.to_datetime(weekly_data["time"].values)

    daily_fast = compute_st_trend_from_config(daily_close, daily_high, daily_low, 10, 3.0, 1)
    daily_slow = compute_st_trend_from_config(daily_close, daily_high, daily_low, 14, 3.5, 3)
    weekly_t1 = compute_st_trend_from_config(weekly_close, weekly_high, weekly_low, 10, 3.0, 1)
    weekly_t2 = compute_st_trend_from_config(weekly_close, weekly_high, weekly_low, 14, 3.0, 2)
    weekly_t3 = compute_st_trend_from_config(weekly_close, weekly_high, weekly_low, 14, 3.5, 3)
    weekly_bull = (weekly_t1 == 1) | (weekly_t2 == 1) | (weekly_t3 == 1)

    weekly_frame = pd.DataFrame({"time": weekly_time, "weekly_bull": weekly_bull}).sort_values(
        "time"
    )
    daily_frame = pd.DataFrame({"time": daily_time}).sort_values("time")
    aligned = pd.merge_asof(daily_frame, weekly_frame, on="time", direction="backward")
    weekly_bull_on_daily = aligned["weekly_bull"].fillna(False).to_numpy(dtype=bool)

    trades: list[dict[str, float]] = []
    in_position = False
    entry_price = 0.0
    entry_time = None
    entry_sigma = 0.0
    entry_bucket = ""
    fast_bear_start = None
    grace_lb = 2

    for i in range(1, len(daily_close)):
        if not in_position:
            sigma_move = entry_sigma_move(daily_close, daily_high, daily_low, i, "D", cone_config)
            buy_cond = (
                daily_fast[i - 1] == -1
                and daily_fast[i] == 1
                and daily_slow[i] == 1
                and weekly_bull_on_daily[i]
                and sigma_move is not None
                and sigma_move < min_negative_sigma
            )
            if buy_cond:
                in_position = True
                entry_price = float(daily_close[i])
                entry_time = daily_time[i]
                entry_sigma = float(sigma_move)
                entry_bucket = sigma_bucket(float(sigma_move))
                fast_bear_start = None
            continue

        if daily_slow[i] == -1:
            append_trade(
                trades,
                entry_price=entry_price,
                exit_price=float(daily_close[i]),
                entry_time=entry_time,
                exit_time=daily_time[i],
                sigma_move=entry_sigma,
                sigma_bucket_value=entry_bucket,
            )
            in_position = False
            fast_bear_start = None
            continue

        if daily_fast[i] == -1:
            fast_bear_start = i if fast_bear_start is None else fast_bear_start
            if i - fast_bear_start >= grace_lb - 1:
                append_trade(
                    trades,
                    entry_price=entry_price,
                    exit_price=float(daily_close[i]),
                    entry_time=entry_time,
                    exit_time=daily_time[i],
                    sigma_move=entry_sigma,
                    sigma_bucket_value=entry_bucket,
                )
                in_position = False
                fast_bear_start = None
        else:
            fast_bear_start = None

    return trades


def summarize_trades(trades: list[dict[str, float]], segment: str) -> list[dict[str, float | str]]:
    grouped: dict[str, list[dict[str, float]]] = defaultdict(list)
    for trade in trades:
        grouped[str(trade["sigma_bucket"])].append(trade)

    summary: list[dict[str, float | str]] = []
    for bucket, bucket_trades in sorted(grouped.items()):
        returns = [trade["return_pct"] for trade in bucket_trades]
        durations = [trade["duration_days"] for trade in bucket_trades]
        wins = [value for value in returns if value > 0]
        summary.append(
            {
                "segment": segment,
                "bucket": bucket,
                "trade_count": len(bucket_trades),
                "avg_return_pct": sum(returns) / len(returns),
                "win_rate_pct": len(wins) / len(returns) * 100.0,
                "median_duration_days": median(durations),
            }
        )
    return summary


def build_report(summary_rows: list[dict[str, float | str]], min_negative_sigma: float) -> str:
    lines = [
        "# Trend Supertrend MTF with Projection Cone Filter",
        "",
        "Rule:",
        "- `D` pullback buy",
        "- `W` already bull",
        f"- `D` cone sigma deviation `< {min_negative_sigma}`",
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


def _chunked(values: list[str], chunk_size: int) -> list[list[str]]:
    return [values[i : i + chunk_size] for i in range(0, len(values), chunk_size)]


def _process_chunk(
    tickers: list[str],
    fetch_data_func,
    cone_config: ProjectionConeConfig,
    min_negative_sigma: float,
) -> list[dict[str, float]]:
    trades: list[dict[str, float]] = []
    for ticker in tickers:
        try:
            daily_data = fetch_data_func(ticker, type="D")
            weekly_data = fetch_data_func(ticker, type="W")
            trades.extend(
                backtest_supertrend_mtf_negative_cone(
                    daily_data,
                    weekly_data,
                    cone_config,
                    min_negative_sigma,
                )
            )
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")
    return trades


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--min-negative-sigma", type=float, default=-1.0)
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--universe", default="all")
    parser.add_argument("--range", dest="range_value", default="all")
    args = parser.parse_args()

    fetch_data_func = get_fetch_data(refresh=args.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    selected_universes = parse_universe_arg(args.universe)
    range_bounds = parse_range_arg(args.range_value)
    output_path = Path("results") / "trend_supertrend_mtf_projection_cone.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\nTesting Trend Supertrend MTF + negative cone filter")
    for segment in selected_universes:
        tickers, effective_range = apply_safe_slice(universes[segment], range_bounds)
        slice_key = f"{segment}_{'all' if effective_range is None else f'{effective_range[0]}_{effective_range[1]}'}"
        segment_trades: list[dict[str, float]] = []
        chunks = _chunked(tickers, args.chunk_size)
        print(
            f"\n{slice_label(segment, effective_range)}: {len(tickers)} tickers across {len(chunks)} chunks"
        )
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {
                executor.submit(
                    _process_chunk,
                    chunk,
                    fetch_data_func,
                    cone_config,
                    args.min_negative_sigma,
                ): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in as_completed(futures):
                chunk_index = futures[future]
                chunk_trades = future.result()
                segment_trades.extend(chunk_trades)
                summary_rows = summarize_trades(segment_trades, segment)
                update_slice_report(
                    output_path,
                    slice_key,
                    build_report(summary_rows, args.min_negative_sigma),
                    "Trend Supertrend MTF with Projection Cone Filter",
                )
                print(
                    f"{segment} chunk {chunk_index}/{len(chunks)} complete "
                    f"(chunk trades={len(chunk_trades)}, segment trades={len(segment_trades)})"
                )
        print(f"{segment} trades={len(segment_trades)}")
        summary_rows = summarize_trades(segment_trades, segment)
        update_slice_report(
            output_path,
            slice_key,
            build_report(summary_rows, args.min_negative_sigma),
            "Trend Supertrend MTF with Projection Cone Filter",
        )
    print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
