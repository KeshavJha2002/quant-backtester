from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

from research.support.selection import (
    apply_safe_slice,
    parse_range_arg,
    parse_universe_arg,
    slice_label,
    update_slice_report,
)
from trading_bot.projection_cone import (
    ProjectionConeConfig,
    _annual_volatility,
    _find_last_pivot,
    _resolve_bars_per_year,
)
from trading_bot.tema_macd.strategy import _tema_macd_state
from trading_bot.utility import (
    config,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


@dataclass(frozen=True)
class TradeRecord:
    ticker: str
    segment: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    return_pct: float
    duration_days: float
    sigma_move: float
    sigma_bucket: str


def _negative_sigma_bucket(sigma_move: float) -> str:
    if sigma_move < -3.0:
        return "< -3σ"
    if sigma_move < -2.0:
        return "-3σ to -2σ"
    if sigma_move < -1.0:
        return "-2σ to -1σ"
    return "excluded"


def _entry_sigma_move(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    idx: int,
    cone_config: ProjectionConeConfig,
) -> float | None:
    bars_per_year = _resolve_bars_per_year("D", cone_config.bars_per_year)
    annual_vol = _annual_volatility(close[: idx + 1], cone_config.vol_length, bars_per_year)
    current_vol = float(annual_vol[-1])
    if np.isnan(current_vol) or current_vol <= 0:
        return None
    anchor_idx = idx
    anchor_price = float(close[idx])
    if cone_config.lock_mode:
        pivot_idx = _find_last_pivot(
            high[: idx + 1], low[: idx + 1], cone_config.pivot_len, cone_config.lock_to_bull
        )
        if pivot_idx is not None and not np.isnan(annual_vol[pivot_idx]):
            anchor_idx = pivot_idx
            anchor_price = float(low[pivot_idx] if cone_config.lock_to_bull else high[pivot_idx])
    t_now = max(idx - anchor_idx, 1)
    return float(
        np.log(float(close[idx]) / anchor_price)
        / (current_vol * np.sqrt(float(t_now) / float(bars_per_year)))
    )


def backtest_tema_macd_mtf_negative_cone(
    daily_data: pd.DataFrame,
    weekly_data: pd.DataFrame,
    ticker: str,
    segment: str,
    cone_config: ProjectionConeConfig,
    min_negative_sigma: float = -1.0,
) -> list[TradeRecord]:
    daily_close = np.asarray(daily_data["close"].values, float).ravel()
    daily_high = np.asarray(daily_data["high"].values, float).ravel()
    daily_low = np.asarray(daily_data["low"].values, float).ravel()
    daily_time = pd.to_datetime(daily_data["time"].values)
    weekly_close = np.asarray(weekly_data["close"].values, float).ravel()
    weekly_time = pd.to_datetime(weekly_data["time"].values)
    daily_tema, daily_macd, daily_signal, daily_state_before, _ = _tema_macd_state(
        daily_close, config
    )
    _, _, _, _, weekly_state_after = _tema_macd_state(weekly_close, config)
    weekly_state_frame = pd.DataFrame(
        {"time": weekly_time, "weekly_bull": weekly_state_after}
    ).sort_values("time")
    daily_frame = pd.DataFrame({"time": daily_time}).sort_values("time")
    aligned = pd.merge_asof(daily_frame, weekly_state_frame, on="time", direction="backward")
    weekly_bull_on_daily = aligned["weekly_bull"].fillna(False).to_numpy(dtype=bool)
    trades: list[TradeRecord] = []
    in_position = False
    last_tran = False
    entry_price = 0.0
    entry_time = None
    entry_sigma = 0.0
    entry_bucket = ""
    for i in range(1, len(daily_close)):
        if np.isnan(daily_tema[i]) or np.isnan(daily_macd[i]) or np.isnan(daily_signal[i]):
            continue
        sigma_move = _entry_sigma_move(daily_close, daily_high, daily_low, i, cone_config)
        sigma_bucket = _negative_sigma_bucket(sigma_move) if sigma_move is not None else "excluded"
        buy_cond = (
            daily_tema[i] >= daily_tema[i - 1]
            and not daily_state_before[i]
            and daily_macd[i] >= daily_signal[i]
            and weekly_bull_on_daily[i]
            and sigma_move is not None
            and sigma_move < min_negative_sigma
        )
        sell_cond = (
            daily_tema[i] < daily_tema[i - 1] and last_tran and daily_macd[i] < daily_signal[i]
        )
        if buy_cond:
            last_tran = True
            if not in_position:
                in_position = True
                entry_price = float(daily_close[i])
                entry_time = daily_time[i]
                entry_sigma = float(sigma_move)
                entry_bucket = sigma_bucket
        elif sell_cond:
            last_tran = False
            if in_position and entry_time is not None:
                exit_price = float(daily_close[i])
                duration = pd.Timestamp(daily_time[i]) - pd.Timestamp(entry_time)
                trades.append(
                    TradeRecord(
                        ticker=ticker,
                        segment=segment,
                        entry_time=str(entry_time),
                        exit_time=str(daily_time[i]),
                        entry_price=entry_price,
                        exit_price=exit_price,
                        return_pct=(exit_price / entry_price - 1.0) * 100.0,
                        duration_days=float(duration / pd.Timedelta(days=1)),
                        sigma_move=entry_sigma,
                        sigma_bucket=entry_bucket,
                    )
                )
                in_position = False
                entry_time = None
    return trades


def summarize_trades(trades: list[TradeRecord]) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str], list[TradeRecord]] = defaultdict(list)
    for trade in trades:
        grouped[(trade.segment, trade.sigma_bucket)].append(trade)
    summary: list[dict[str, float | str]] = []
    for (segment, bucket), bucket_trades in sorted(grouped.items()):
        returns = [trade.return_pct for trade in bucket_trades]
        durations = [trade.duration_days for trade in bucket_trades]
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


def build_report(summary_rows: list[dict[str, float | str]], trades: list[TradeRecord]) -> str:
    sections = [
        "# TEMA-MACD MTF with Projection Cone Filter",
        "",
        "Rule:",
        "- `D` fresh buy",
        "- `W` already bullish",
        "- Daily cone sigma deviation `< -1`",
        "",
        "## Summary by Negative Cone Bucket",
        "| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        sections.append(
            f"| {row['segment']} | {row['bucket']} | {row['trade_count']} | {row['avg_return_pct']:.2f} | "
            f"{row['win_rate_pct']:.2f} | {row['median_duration_days']:.2f} |"
        )
    sections.extend(["", "## Total", f"- Total trades analyzed: `{len(trades)}`"])
    return "\n".join(sections)


def _chunked(values: list[str], chunk_size: int) -> list[list[str]]:
    return [values[i : i + chunk_size] for i in range(0, len(values), chunk_size)]


def _process_chunk(
    tickers: list[str],
    segment: str,
    fetch_data_func,
    cone_config: ProjectionConeConfig,
    min_negative_sigma: float,
) -> list[TradeRecord]:
    trades: list[TradeRecord] = []
    for ticker in tickers:
        try:
            daily_data = fetch_data_func(ticker, type="D")
            weekly_data = fetch_data_func(ticker, type="W")
            trades.extend(
                backtest_tema_macd_mtf_negative_cone(
                    daily_data,
                    weekly_data,
                    ticker,
                    segment,
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
    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    selected_universes = parse_universe_arg(args.universe)
    range_bounds = parse_range_arg(args.range_value)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    output_path = Path("results") / "tema_macd_mtf_projection_cone.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    print("\nTesting TEMA-MACD MTF + negative cone filter")
    for segment in selected_universes:
        tickers, effective_range = apply_safe_slice(universes[segment], range_bounds)
        slice_key = f"{segment}_{'all' if effective_range is None else f'{effective_range[0]}_{effective_range[1]}'}"
        slice_trades: list[TradeRecord] = []
        segment_trade_count = 0
        chunks = _chunked(tickers, args.chunk_size)
        print(
            f"\n{slice_label(segment, effective_range)}: {len(tickers)} tickers across {len(chunks)} chunks"
        )
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {
                executor.submit(
                    _process_chunk,
                    chunk,
                    segment,
                    fetch_data_func,
                    cone_config,
                    args.min_negative_sigma,
                ): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in as_completed(futures):
                chunk_index = futures[future]
                chunk_trades = future.result()
                slice_trades.extend(chunk_trades)
                segment_trade_count += len(chunk_trades)
                current_summary = summarize_trades(slice_trades)
                update_slice_report(
                    output_path,
                    slice_key,
                    build_report(current_summary, slice_trades),
                    "TEMA-MACD MTF with Projection Cone Filter",
                )
                print(
                    f"{segment} chunk {chunk_index}/{len(chunks)} complete "
                    f"(chunk trades={len(chunk_trades)}, segment trades={segment_trade_count})"
                )
        print(f"{segment} trades={segment_trade_count}")
        summary_rows = summarize_trades(slice_trades)
        update_slice_report(
            output_path,
            slice_key,
            build_report(summary_rows, slice_trades),
            "TEMA-MACD MTF with Projection Cone Filter",
        )
    print(f"\nSaved report to {output_path}")
