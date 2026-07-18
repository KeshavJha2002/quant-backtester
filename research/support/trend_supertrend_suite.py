from __future__ import annotations

import argparse
from dataclasses import dataclass
from statistics import median

import numpy as np
import pandas as pd

from trading_bot.utility import (
    compute_st_trend_from_config,
    fetch_data,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


@dataclass(frozen=True)
class MetricExpectation:
    avg_return_pct: float
    win_rate_pct: float
    median_duration_days: float


EXPECTED_RESULTS: dict[str, dict[str, MetricExpectation]] = {
    "D": {
        "N50": MetricExpectation(7.22, 43.01, 79.00),
        "N150": MetricExpectation(14.38, 45.51, 87.00),
        "N250": MetricExpectation(23.41, 47.19, 93.00),
    },
    "W": {
        "N50": MetricExpectation(115.57, 55.98, 497.00),
        "N150": MetricExpectation(158.48, 51.60, 504.00),
        "N250": MetricExpectation(109.32, 52.68, 483.00),
    },
}


def _metrics_from_trades(trades: list[dict[str, float]], label: str) -> dict[str, float]:
    if not trades:
        raise ValueError(f"No trades generated for {label}")
    returns = [trade["return_pct"] for trade in trades]
    durations = [trade["duration_days"] for trade in trades]
    wins = [value for value in returns if value > 0]
    return {
        "trade_count": float(len(trades)),
        "avg_return_pct": float(sum(returns) / len(returns)),
        "win_rate_pct": float(len(wins) / len(returns) * 100.0),
        "median_duration_days": float(median(durations)),
    }


def _append_trade(
    trades: list[dict[str, float]], entry_price: float, exit_price: float, entry_time, exit_time
) -> None:
    duration = pd.Timestamp(exit_time) - pd.Timestamp(entry_time)
    trades.append(
        {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "return_pct": (exit_price / entry_price - 1.0) * 100.0,
            "duration_days": float(duration / pd.Timedelta(days=1)),
        }
    )


def backtest_supertrend_daily(data) -> list[dict[str, float]]:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()
    time_values = pd.to_datetime(data["time"].values)
    trend_fast = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend_slow = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)
    trades: list[dict[str, float]] = []
    in_position = False
    entry_price = 0.0
    entry_time = None
    fast_bear_start = None
    grace_lb = 2
    for i in range(1, len(close)):
        if not in_position:
            if trend_fast[i - 1] == -1 and trend_fast[i] == 1 and trend_slow[i] == 1:
                in_position = True
                entry_price = float(close[i])
                entry_time = time_values[i]
                fast_bear_start = None
            continue
        if trend_slow[i] == -1:
            _append_trade(trades, entry_price, float(close[i]), entry_time, time_values[i])
            in_position = False
            fast_bear_start = None
            continue
        if trend_fast[i] == -1:
            fast_bear_start = i if fast_bear_start is None else fast_bear_start
            if i - fast_bear_start >= grace_lb - 1:
                _append_trade(trades, entry_price, float(close[i]), entry_time, time_values[i])
                in_position = False
                fast_bear_start = None
        else:
            fast_bear_start = None
    return trades


def backtest_supertrend_weekly(data) -> list[dict[str, float]]:
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
    for i in range(1, len(close)):
        bullish_flip = (
            (trend1[i - 1] == -1 and trend1[i] == 1)
            or (trend2[i - 1] == -1 and trend2[i] == 1)
            or (trend3[i - 1] == -1 and trend3[i] == 1)
        )
        all_bearish = trend1[i] == -1 and trend2[i] == -1 and trend3[i] == -1
        if not in_position and bullish_flip:
            in_position = True
            entry_price = float(close[i])
            entry_time = time_values[i]
            continue
        if in_position and all_bearish:
            _append_trade(trades, entry_price, float(close[i]), entry_time, time_values[i])
            in_position = False
    return trades


def backtest_supertrend_mtf(daily_data, weekly_data) -> list[dict[str, float]]:
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
    fast_bear_start = None
    grace_lb = 2
    for i in range(1, len(daily_close)):
        if not in_position:
            if (
                daily_fast[i - 1] == -1
                and daily_fast[i] == 1
                and daily_slow[i] == 1
                and weekly_bull_on_daily[i]
            ):
                in_position = True
                entry_price = float(daily_close[i])
                entry_time = daily_time[i]
                fast_bear_start = None
            continue
        if daily_slow[i] == -1:
            _append_trade(trades, entry_price, float(daily_close[i]), entry_time, daily_time[i])
            in_position = False
            fast_bear_start = None
            continue
        if daily_fast[i] == -1:
            fast_bear_start = i if fast_bear_start is None else fast_bear_start
            if i - fast_bear_start >= grace_lb - 1:
                _append_trade(trades, entry_price, float(daily_close[i]), entry_time, daily_time[i])
                in_position = False
                fast_bear_start = None
        else:
            fast_bear_start = None
    return trades


def compute_metrics(tickers: list[str], freq: str, fetch_data_func=fetch_data) -> dict[str, float]:
    all_trades: list[dict[str, float]] = []
    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            all_trades.extend(
                backtest_supertrend_daily(data) if freq == "D" else backtest_supertrend_weekly(data)
            )
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")
    return _metrics_from_trades(all_trades, f"supertrend {freq}")


def compute_mtf_metrics(tickers: list[str], fetch_data_func=fetch_data) -> dict[str, float]:
    all_trades: list[dict[str, float]] = []
    for ticker in tickers:
        try:
            daily_data = fetch_data_func(ticker, type="D")
            weekly_data = fetch_data_func(ticker, type="W")
            all_trades.extend(backtest_supertrend_mtf(daily_data, weekly_data))
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")
    return _metrics_from_trades(all_trades, "supertrend mtf")


def check_close(label: str, actual: float, expected: float, tolerance: float) -> str | None:
    delta = abs(actual - expected)
    status = "PASS" if delta <= tolerance else "FAIL"
    print(
        f"{status} {label}: actual={actual:.2f}, expected={expected:.2f}, delta={delta:.2f}, tolerance={tolerance:.2f}"
    )
    if delta > tolerance:
        return f"{label} outside tolerance"
    return None


def print_mtf_performance(fetch_data_func=fetch_data) -> None:
    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    print("\nSupertrend MTF Performance (D pullback within W bull)")
    for segment, tickers in universes.items():
        metrics = compute_mtf_metrics(tickers, fetch_data_func=fetch_data_func)
        print(f"\n{segment}")
        print(f"Trade Count           : {int(metrics['trade_count'])}")
        print(f"Avg Return per Trade  : {metrics['avg_return_pct']:.2f}%")
        print(f"Win Rate              : {metrics['win_rate_pct']:.2f}%")
        print(f"Median Trade Duration : {metrics['median_duration_days']:.2f} days")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()
    fetch_data_func = get_fetch_data(refresh=args.refresh_data)

    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    tolerances = {
        "D": {"avg_return_pct": 15.0, "win_rate_pct": 10.0, "median_duration_days": 40.0},
        "W": {"avg_return_pct": 75.0, "win_rate_pct": 10.0, "median_duration_days": 50.0},
    }
    failures: list[str] = []
    for freq, expected_by_segment in EXPECTED_RESULTS.items():
        print(f"\nTesting Supertrend {freq}")
        for segment, tickers in universes.items():
            metrics = compute_metrics(tickers, freq, fetch_data_func=fetch_data_func)
            expected = expected_by_segment[segment]
            freq_tolerance = tolerances[freq]
            print(f"\n{segment} trade_count={int(metrics['trade_count'])}")
            for key, expected_value, tol_key in [
                ("avg_return_pct", expected.avg_return_pct, "avg_return_pct"),
                ("win_rate_pct", expected.win_rate_pct, "win_rate_pct"),
                ("median_duration_days", expected.median_duration_days, "median_duration_days"),
            ]:
                result = check_close(
                    f"{freq} {segment} {key}", metrics[key], expected_value, freq_tolerance[tol_key]
                )
                if result:
                    failures.append(result)
    print_mtf_performance(fetch_data_func=fetch_data_func)
    if failures:
        raise AssertionError("\n".join(failures))
