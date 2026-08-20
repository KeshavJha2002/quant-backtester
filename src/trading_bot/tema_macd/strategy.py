from __future__ import annotations

from collections.abc import Callable, Iterable

import numpy as np
import pandas as pd

from trading_bot.utility import (
    ema,
    latest_complete_bar_index,
    rma,
    sma,
    true_range,
)


def compute_tema_macd_state(
    close: np.ndarray, config: dict[str, int]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute Triple EMA, MACD, Signal, and boolean state arrays before and after each candle bar."""
    close = np.asarray(close, dtype=float).ravel()
    ema1 = ema(close, config["tema_len"])
    ema2 = ema(ema1, config["tema_len"])
    ema3 = ema(ema2, config["tema_len"])
    tema = 3 * (ema1 - ema2) + ema3

    fast = ema(close, config["macd_fast"])
    slow = ema(close, config["macd_slow"])
    macd = fast - slow
    signal = sma(macd, config["macd_signal"])

    last_tran = False
    state_before_bar = np.zeros(len(close), dtype=bool)
    state_after_bar = np.zeros(len(close), dtype=bool)

    for i in range(1, len(close)):
        if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
            state_before_bar[i] = last_tran
            state_after_bar[i] = last_tran
            continue

        state_before_bar[i] = last_tran

        if tema[i] >= tema[i - 1] and not last_tran and macd[i] >= signal[i]:
            last_tran = True
        elif tema[i] < tema[i - 1] and last_tran and macd[i] < signal[i]:
            last_tran = False

        state_after_bar[i] = last_tran

    return tema, macd, signal, state_before_bar, state_after_bar


def calculate_atr_percent(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int = 14
) -> np.ndarray:
    """Calculate ATR as a percentage of close price."""
    tr = true_range(high, low, close)
    atr = rma(tr, length)
    return (atr / close) * 100.0


def tema_macd_fresh_bull_screen(
    tickers: Iterable[str],
    fetch_data_func: Callable[..., pd.DataFrame],
    freq: str,
    config: dict[str, int],
) -> list[str]:
    """Scan tickers for a fresh bullish TEMA-MACD signal on the latest complete bar."""
    buy_list: list[str] = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            close = np.asarray(data["close"].values, dtype=float).ravel()
            time_values = np.asarray(data["time"].values)

            if len(close) < max(config["tema_len"], config["macd_slow"]) + 5:
                continue

            i = latest_complete_bar_index(time_values, freq)
            if i is None or i <= 0:
                continue

            tema, macd, signal, state_before_bar, _ = compute_tema_macd_state(close, config)
            if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
                continue

            fresh_buy = bool(
                tema[i] >= tema[i - 1]
                and not state_before_bar[i]
                and macd[i] >= signal[i]
            )

            if fresh_buy:
                buy_list.append(ticker)

        except Exception as e:
            print(ticker, e)

    return buy_list


def tema_macd_active_bull_screen(
    tickers: Iterable[str],
    fetch_data_func: Callable[..., pd.DataFrame],
    freq: str,
    config: dict[str, int],
) -> list[str]:
    """Scan tickers for an active bullish TEMA-MACD state on the latest complete bar."""
    buy_list: list[str] = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            close = np.asarray(data["close"].values, dtype=float).ravel()
            time_values = np.asarray(data["time"].values)

            if len(close) < max(config["tema_len"], config["macd_slow"]) + 5:
                continue

            i = latest_complete_bar_index(time_values, freq)
            if i is None:
                continue

            _, _, _, _, state_after_bar = compute_tema_macd_state(close, config)

            if state_after_bar[i]:
                buy_list.append(ticker)

        except Exception as e:
            print(ticker, e)

    return buy_list


def tema_macd_fresh_bull_screen_tight(
    tickers: Iterable[str],
    fetch_data_func: Callable[..., pd.DataFrame],
    freq: str,
    config: dict[str, int],
    *,
    trend_ema_len: int = 200,
    trend_slope_lookback: int = 5,
    min_atr_pct: float = 1.0,
    breakout_lookback: int = 5,
) -> list[str]:
    """Scan tickers for fresh TEMA-MACD signal with strict trend, momentum, ATR, and breakout filters."""
    buy_list: list[str] = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            close = np.asarray(data["close"].values, dtype=float).ravel()
            high = np.asarray(data["high"].values, dtype=float).ravel()
            low = np.asarray(data["low"].values, dtype=float).ravel()
            time_values = np.asarray(data["time"].values)

            if len(close) < max(config["tema_len"], config["macd_slow"], trend_ema_len) + 5:
                continue

            trend_ema = ema(close, trend_ema_len)
            atr_pct = calculate_atr_percent(high, low, close, 14)

            i = latest_complete_bar_index(time_values, freq)
            if i is None or i <= 0:
                continue

            tema, macd, signal, state_before_bar, _ = compute_tema_macd_state(close, config)
            if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
                continue

            fresh_buy = bool(
                tema[i] >= tema[i - 1]
                and not state_before_bar[i]
                and macd[i] >= signal[i]
            )

            if not fresh_buy:
                continue

            if i - trend_slope_lookback < 0:
                continue
            trend_ok = bool(
                close[i] > trend_ema[i] and trend_ema[i] > trend_ema[i - trend_slope_lookback]
            )
            momentum_ok = bool(macd[i] > 0 and signal[i] > 0)
            volatility_ok = bool(atr_pct[i] >= min_atr_pct)

            if breakout_lookback > 0:
                hh = np.nanmax(high[max(0, i - breakout_lookback) : i])
                breakout_ok = bool(close[i] > hh)
            else:
                breakout_ok = True

            if trend_ok and momentum_ok and volatility_ok and breakout_ok:
                buy_list.append(ticker)

        except Exception as e:
            print(ticker, e)

    return buy_list


# Backward-compatible aliases
_tema_macd_state = compute_tema_macd_state
_atr_percent = calculate_atr_percent
_latest_complete_bar_index = latest_complete_bar_index
