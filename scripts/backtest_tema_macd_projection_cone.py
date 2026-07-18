from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import pandas as pd

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    _annual_volatility,
    _find_last_pivot,
    _resolve_bars_per_year,
)
from trading_bot.utility import (
    config,
    ema,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
    sma,
)


@dataclass(frozen=True)
class TradeRecord:
    ticker: str
    segment: str
    timeframe: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    return_pct: float
    duration_days: float
    sigma_move: float
    sigma_bucket: str


def _sigma_bucket(sigma_move: float) -> str:
    if sigma_move < -3.0:
        return "< -3σ"
    if sigma_move < -2.0:
        return "-3σ to -2σ"
    if sigma_move < -1.0:
        return "-2σ to -1σ"
    if sigma_move < 0.0:
        return "-1σ to 0σ"
    if sigma_move < 1.0:
        return "0σ to +1σ"
    if sigma_move < 2.0:
        return "+1σ to +2σ"
    if sigma_move < 3.0:
        return "+2σ to +3σ"
    return "> +3σ"


def _entry_sigma_move(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    idx: int,
    freq: str,
    cone_config: ProjectionConeConfig,
) -> float | None:
    bars_per_year = _resolve_bars_per_year(freq, cone_config.bars_per_year)
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
    sigma_move = float(
        np.log(float(close[idx]) / anchor_price)
        / (current_vol * np.sqrt(float(t_now) / float(bars_per_year)))
    )
    return sigma_move


def backtest_tema_macd_with_cone(
    data: pd.DataFrame,
    ticker: str,
    segment: str,
    freq: str,
    cone_config: ProjectionConeConfig,
) -> list[TradeRecord]:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()
    time_values = pd.to_datetime(data["time"].values)

    ema1 = ema(close, config["tema_len"])
    ema2 = ema(ema1, config["tema_len"])
    ema3 = ema(ema2, config["tema_len"])
    tema = 3 * (ema1 - ema2) + ema3

    fast = ema(close, config["macd_fast"])
    slow = ema(close, config["macd_slow"])
    macd = fast - slow
    signal = sma(macd, config["macd_signal"])

    trades: list[TradeRecord] = []
    in_position = False
    last_tran = False
    entry_price = 0.0
    entry_time = None
    entry_sigma = 0.0
    entry_bucket = ""

    for i in range(1, len(close)):
        if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
            continue

        buy_cond = tema[i] >= tema[i - 1] and not last_tran and macd[i] >= signal[i]
        sell_cond = tema[i] < tema[i - 1] and last_tran and macd[i] < signal[i]

        if buy_cond:
            last_tran = True
            sigma_move = _entry_sigma_move(close, high, low, i, freq, cone_config)
            if sigma_move is None:
                continue
            if not in_position:
                in_position = True
                entry_price = float(close[i])
                entry_time = time_values[i]
                entry_sigma = sigma_move
                entry_bucket = _sigma_bucket(sigma_move)

        elif sell_cond:
            last_tran = False
            if in_position and entry_time is not None:
                exit_price = float(close[i])
                duration = pd.Timestamp(time_values[i]) - pd.Timestamp(entry_time)
                trades.append(
                    TradeRecord(
                        ticker=ticker,
                        segment=segment,
                        timeframe=freq,
                        entry_time=str(entry_time),
                        exit_time=str(time_values[i]),
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


def summarize_bucket_performance(trades: list[TradeRecord]) -> list[dict[str, float | str]]:
    grouped: dict[tuple[str, str, str], list[TradeRecord]] = defaultdict(list)
    for trade in trades:
        grouped[(trade.timeframe, trade.segment, trade.sigma_bucket)].append(trade)

    summary: list[dict[str, float | str]] = []
    for (timeframe, segment, bucket), bucket_trades in sorted(grouped.items()):
        returns = [trade.return_pct for trade in bucket_trades]
        durations = [trade.duration_days for trade in bucket_trades]
        wins = [value for value in returns if value > 0]
        summary.append(
            {
                "timeframe": timeframe,
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
        "# TEMA-MACD with Projection Cone",
        "",
        "## Summary by Cone Bucket",
        "| Timeframe | Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        sections.append(
            f"| {row['timeframe']} | {row['segment']} | {row['bucket']} | "
            f"{row['trade_count']} | {row['avg_return_pct']:.2f} | "
            f"{row['win_rate_pct']:.2f} | {row['median_duration_days']:.2f} |"
        )

    sections.extend(
        [
            "",
            "## Negative Sigma Focus",
            "| Timeframe | Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in summary_rows:
        bucket = str(row["bucket"])
        if bucket in {"-1σ to 0σ", "-2σ to -1σ", "-3σ to -2σ", "< -3σ"}:
            sections.append(
                f"| {row['timeframe']} | {row['segment']} | {bucket} | "
                f"{row['trade_count']} | {row['avg_return_pct']:.2f} | "
                f"{row['win_rate_pct']:.2f} | {row['median_duration_days']:.2f} |"
            )

    sections.extend(
        [
            "",
            "## Trade Count",
            f"- Total trades analyzed: `{len(trades)}`",
        ]
    )
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()
    fetch_data_func = get_fetch_data(refresh=args.refresh_data)

    universes = {
        "N50": nifty50_ns,
        "N150": nifty150_ns,
        "N250": nifty250_ns,
    }
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)

    all_trades: list[TradeRecord] = []
    for freq in ("D", "W"):
        print(f"\nTesting TEMA-MACD + Cone on {freq}")
        for segment, tickers in universes.items():
            segment_trade_count = 0
            for ticker in tickers:
                try:
                    data = fetch_data_func(ticker, type=freq)
                    trades = backtest_tema_macd_with_cone(data, ticker, segment, freq, cone_config)
                    all_trades.extend(trades)
                    segment_trade_count += len(trades)
                except Exception as exc:
                    print(f"Skipping {ticker} {freq}: {exc}")
            print(f"{segment} trades={segment_trade_count}")

    summary_rows = summarize_bucket_performance(all_trades)
    report = build_report(summary_rows, all_trades)
    output_path = Path("results") / "tema_macd_projection_cone.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
