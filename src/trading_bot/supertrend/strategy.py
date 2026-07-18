from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

import numpy as np
import pandas as pd

from trading_bot.tema_macd.strategy import _latest_complete_bar_index
from trading_bot.utility import compute_st_trend_from_config


def supertrend_or_regime_filter(
    ticker: str,
    data: pd.DataFrame,
    freq: str,
    bull_trend_tickers: dict[str, list[str]],
    recent_5: dict[str, list[str]],
    recent_2: dict[str, list[str]],
) -> None:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()

    trend1 = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend2 = compute_st_trend_from_config(close, high, low, 14, 3.0, 2)
    trend3 = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)

    n = len(close)

    if trend1[-1] == 1 or trend2[-1] == 1 or trend3[-1] == 1:
        bull_trend_tickers[freq].append(ticker)

    for lb, store in [(5, recent_5), (1, recent_2)]:
        for i in range(max(1, n - lb), n):
            if (
                (trend1[i - 1] == -1 and trend1[i] == 1)
                or (trend2[i - 1] == -1 and trend2[i] == 1)
                or (trend3[i - 1] == -1 and trend3[i] == 1)
            ):
                store[freq].append(ticker)
                break


def supertrend_regime_pullback_filter(
    ticker: str,
    data: pd.DataFrame,
    freq: str,
    bull_trend_tickers: dict[str, list[str]],
    recent_5: dict[str, list[str]],
    recent_2: dict[str, list[str]],
) -> None:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()

    trend_fast = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend_slow = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)

    n = len(close)

    if trend_slow[-1] == 1:
        bull_trend_tickers[freq].append(ticker)

    for lb, store in [(5, recent_5), (1, recent_2)]:
        for i in range(max(1, n - lb), n):
            if trend_fast[i - 1] == -1 and trend_fast[i] == 1 and trend_slow[i] == 1:
                store[freq].append(ticker)
                break


def supertrend_regime_exit_filter(
    bought_tickers: Iterable[str],
    fetch_data_func,
    freq: str,
    grace_lb: int = 2,
) -> dict[str, str]:
    decision: dict[str, str] = {}

    for ticker in bought_tickers:
        try:
            data = fetch_data_func(ticker, type=freq)

            close = np.asarray(data["close"].values, float).ravel()
            high = np.asarray(data["high"].values, float).ravel()
            low = np.asarray(data["low"].values, float).ravel()

            trend_fast = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
            trend_slow = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)

            n = len(close)

            if trend_slow[-1] == -1:
                decision[ticker] = "sell"
                continue

            if trend_fast[-1] == -1:
                recovered = False
                for i in range(max(1, n - grace_lb), n):
                    if trend_fast[i] == 1:
                        recovered = True
                        break

                if not recovered:
                    decision[ticker] = "sell"
                    continue

            decision[ticker] = "hold"

        except Exception:
            decision[ticker] = "hold"

    return decision


def run_supertrend_scans(
    tickers: Iterable[str],
    fetch_data_func,
    freq: str,
    mode: str,
) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    bull = defaultdict(list)
    recent_5 = defaultdict(list)
    recent_2 = defaultdict(list)

    for ticker in tickers:
        data = fetch_data_func(ticker, type=freq)
        complete_idx = _latest_complete_bar_index(np.asarray(data["time"].values), freq)
        if complete_idx is None or complete_idx <= 0:
            continue
        data = data.iloc[: complete_idx + 1].reset_index(drop=True)
        if mode == "pullback":
            supertrend_regime_pullback_filter(ticker, data, freq, bull, recent_5, recent_2)
        else:
            supertrend_or_regime_filter(ticker, data, freq, bull, recent_5, recent_2)

    return bull, recent_5, recent_2
