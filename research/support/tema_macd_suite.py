from __future__ import annotations

import argparse
from dataclasses import dataclass
from statistics import median

import numpy as np
import pandas as pd

from trading_bot.tema_macd.strategy import _tema_macd_state
from trading_bot.utility import (
    config,
    ema,
    fetch_data,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
    sma,
)


@dataclass(frozen=True)
class MetricExpectation:
    avg_return_pct: float
    win_rate_pct: float
    median_duration_days: float


EXPECTED_RESULTS: dict[str, dict[str, MetricExpectation]] = {
    "D": {
        "N50": MetricExpectation(1.15, 41.90, 15.00),
        "N150": MetricExpectation(1.59, 40.29, 15.00),
        "N250": MetricExpectation(1.94, 39.39, 15.00),
    },
    "W": {
        "N50": MetricExpectation(8.46, 46.56, 77.00),
        "N150": MetricExpectation(9.47, 44.19, 77.00),
        "N250": MetricExpectation(11.86, 43.16, 77.00),
    },
}


def backtest_tema_macd_strategy(data) -> list[dict[str, float]]:
    close = np.asarray(data["close"].values, float).ravel()
    time_values = pd.to_datetime(data["time"].values)

    ema1 = ema(close, config["tema_len"])
    ema2 = ema(ema1, config["tema_len"])
    ema3 = ema(ema2, config["tema_len"])
    tema = 3 * (ema1 - ema2) + ema3

    fast = ema(close, config["macd_fast"])
    slow = ema(close, config["macd_slow"])
    macd = fast - slow
    signal = sma(macd, config["macd_signal"])

    trades: list[dict[str, float]] = []
    in_position = False
    last_tran = False
    entry_price = 0.0
    entry_time = None

    for i in range(1, len(close)):
        if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
            continue

        buy_cond = tema[i] >= tema[i - 1] and not last_tran and macd[i] >= signal[i]
        sell_cond = tema[i] < tema[i - 1] and last_tran and macd[i] < signal[i]

        if buy_cond:
            last_tran = True
            if not in_position:
                in_position = True
                entry_price = float(close[i])
                entry_time = time_values[i]

        elif sell_cond:
            last_tran = False
            if in_position and entry_time is not None:
                exit_price = float(close[i])
                duration = pd.Timestamp(time_values[i]) - pd.Timestamp(entry_time)
                trades.append(
                    {
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return_pct": (exit_price / entry_price - 1.0) * 100.0,
                        "duration_days": float(duration / pd.Timedelta(days=1)),
                    }
                )
                in_position = False
                entry_time = None

    return trades


def compute_metrics(tickers: list[str], freq: str, fetch_data_func=fetch_data) -> dict[str, float]:
    all_trades: list[dict[str, float]] = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            all_trades.extend(backtest_tema_macd_strategy(data))
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")

    if not all_trades:
        raise ValueError(f"No trades generated for freq={freq}")

    returns = [trade["return_pct"] for trade in all_trades]
    durations = [trade["duration_days"] for trade in all_trades]
    wins = [value for value in returns if value > 0]

    return {
        "trade_count": float(len(all_trades)),
        "avg_return_pct": float(sum(returns) / len(returns)),
        "win_rate_pct": float(len(wins) / len(returns) * 100.0),
        "median_duration_days": float(median(durations)),
    }


def assert_close(label: str, actual: float, expected: float, tolerance: float) -> None:
    delta = abs(actual - expected)
    status = "PASS" if delta <= tolerance else "FAIL"
    print(
        f"{status} {label}: actual={actual:.2f}, expected={expected:.2f}, "
        f"delta={delta:.2f}, tolerance={tolerance:.2f}"
    )
    if delta > tolerance:
        raise AssertionError(f"{label} outside tolerance")


def backtest_tema_macd_mtf_strategy(daily_data, weekly_data) -> list[dict[str, float]]:
    daily_close = np.asarray(daily_data["close"].values, float).ravel()
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

    trades: list[dict[str, float]] = []
    in_position = False
    last_tran = False
    entry_price = 0.0
    entry_time = None

    for i in range(1, len(daily_close)):
        if np.isnan(daily_tema[i]) or np.isnan(daily_macd[i]) or np.isnan(daily_signal[i]):
            continue

        buy_cond = (
            daily_tema[i] >= daily_tema[i - 1]
            and not daily_state_before[i]
            and daily_macd[i] >= daily_signal[i]
            and weekly_bull_on_daily[i]
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

        elif sell_cond:
            last_tran = False
            if in_position and entry_time is not None:
                exit_price = float(daily_close[i])
                duration = pd.Timestamp(daily_time[i]) - pd.Timestamp(entry_time)
                trades.append(
                    {
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "return_pct": (exit_price / entry_price - 1.0) * 100.0,
                        "duration_days": float(duration / pd.Timedelta(days=1)),
                    }
                )
                in_position = False
                entry_time = None

    return trades


def compute_mtf_metrics(tickers: list[str], fetch_data_func=fetch_data) -> dict[str, float]:
    all_trades: list[dict[str, float]] = []
    for ticker in tickers:
        try:
            daily_data = fetch_data_func(ticker, type="D")
            weekly_data = fetch_data_func(ticker, type="W")
            all_trades.extend(backtest_tema_macd_mtf_strategy(daily_data, weekly_data))
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")

    if not all_trades:
        raise ValueError("No MTF trades generated")

    returns = [trade["return_pct"] for trade in all_trades]
    durations = [trade["duration_days"] for trade in all_trades]
    wins = [value for value in returns if value > 0]
    return {
        "trade_count": float(len(all_trades)),
        "avg_return_pct": float(sum(returns) / len(returns)),
        "win_rate_pct": float(len(wins) / len(returns) * 100.0),
        "median_duration_days": float(median(durations)),
    }


def print_mtf_performance(fetch_data_func=fetch_data) -> None:
    universes = {"N50": nifty50_ns, "N150": nifty150_ns, "N250": nifty250_ns}
    print("\nTEMA-MACD MTF Performance (D entry within W bull)")
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
    tolerances = {"avg_return_pct": 2.0, "win_rate_pct": 5.0, "median_duration_days": 10.0}

    for freq, expected_by_segment in EXPECTED_RESULTS.items():
        print(f"\nTesting TEMA-MACD {freq}")
        for segment, tickers in universes.items():
            metrics = compute_metrics(tickers, freq, fetch_data_func=fetch_data_func)
            expected = expected_by_segment[segment]
            print(f"\n{segment} trade_count={int(metrics['trade_count'])}")
            assert_close(
                f"{freq} {segment} avg_return_pct",
                metrics["avg_return_pct"],
                expected.avg_return_pct,
                tolerances["avg_return_pct"],
            )
            assert_close(
                f"{freq} {segment} win_rate_pct",
                metrics["win_rate_pct"],
                expected.win_rate_pct,
                tolerances["win_rate_pct"],
            )
            assert_close(
                f"{freq} {segment} median_duration_days",
                metrics["median_duration_days"],
                expected.median_duration_days,
                tolerances["median_duration_days"],
            )

    print_mtf_performance(fetch_data_func=fetch_data_func)
