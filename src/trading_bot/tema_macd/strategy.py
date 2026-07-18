from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from trading_bot.utility import ema, rma, sma, true_range

MARKET_TZ = ZoneInfo("Asia/Kolkata")
MARKET_CLOSE = time(15, 30)


def _latest_complete_bar_index(time_values, freq: str) -> int | None:
    if len(time_values) == 0:
        return None

    timestamps = []
    for value in time_values:
        ts = pd.to_datetime(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize(MARKET_TZ)
        else:
            ts = ts.tz_convert(MARKET_TZ)
        timestamps.append(ts.to_pydatetime())

    now = datetime.now(MARKET_TZ)
    last_idx = len(timestamps) - 1
    last_ts = timestamps[last_idx]
    last_date = last_ts.date()
    today = now.date()

    if freq == "D":
        if last_date < today:
            return last_idx
        if last_date > today:
            return last_idx - 1 if last_idx > 0 else None
        if now.weekday() < 5 and now.time() < MARKET_CLOSE:
            return last_idx - 1 if last_idx > 0 else None
        return last_idx

    if freq == "W":
        current_week_start = today.fromordinal(today.toordinal() - today.weekday())
        if last_date < current_week_start:
            return last_idx
        if last_date > current_week_start:
            return last_idx - 1 if last_idx > 0 else None
        week_complete = now.weekday() > 4 or (now.weekday() == 4 and now.time() >= MARKET_CLOSE)
        if not week_complete:
            return last_idx - 1 if last_idx > 0 else None
        return last_idx

    return last_idx


def _tema_macd_state(
    close: np.ndarray, config
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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


def tema_macd_fresh_bull_screen(tickers, fetch_data_func, freq, config):
    buy_list = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            close = np.asarray(data["close"].values, dtype=float).ravel()
            time_values = np.asarray(data["time"].values)

            if len(close) < max(config["tema_len"], config["macd_slow"]) + 5:
                continue

            i = _latest_complete_bar_index(time_values, freq)
            if i is None or i <= 0:
                continue

            tema, macd, signal, state_before_bar, _ = _tema_macd_state(close, config)
            if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
                continue

            fresh_buy = tema[i] >= tema[i - 1] and not state_before_bar[i] and macd[i] >= signal[i]

            if fresh_buy:
                buy_list.append(ticker)

        except Exception as e:
            print(ticker, e)

    return buy_list


def tema_macd_active_bull_screen(tickers, fetch_data_func, freq, config):
    buy_list = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            close = np.asarray(data["close"].values, dtype=float).ravel()
            time_values = np.asarray(data["time"].values)

            if len(close) < max(config["tema_len"], config["macd_slow"]) + 5:
                continue

            i = _latest_complete_bar_index(time_values, freq)
            if i is None:
                continue

            _, _, _, _, state_after_bar = _tema_macd_state(close, config)

            if state_after_bar[i]:
                buy_list.append(ticker)

        except Exception as e:
            print(ticker, e)

    return buy_list


def _atr_percent(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int) -> np.ndarray:
    tr = true_range(high, low, close)
    atr = rma(tr, length)
    return (atr / close) * 100.0


def tema_macd_fresh_bull_screen_tight(
    tickers,
    fetch_data_func,
    freq,
    config,
    *,
    trend_ema_len: int = 200,
    trend_slope_lookback: int = 5,
    min_atr_pct: float = 1.0,
    breakout_lookback: int = 5,
):
    buy_list = []

    for ticker in tickers:
        try:
            data = fetch_data_func(ticker, type=freq)
            close = np.asarray(data["close"].values, dtype=float).ravel()
            high = np.asarray(data["high"].values, dtype=float).ravel()
            time_values = np.asarray(data["time"].values)

            if len(close) < max(config["tema_len"], config["macd_slow"], trend_ema_len) + 5:
                continue

            trend_ema = ema(close, trend_ema_len)
            atr_pct = _atr_percent(
                high, np.asarray(data["low"].values, dtype=float).ravel(), close, 14
            )

            i = _latest_complete_bar_index(time_values, freq)
            if i is None or i <= 0:
                continue

            tema, macd, signal, state_before_bar, _ = _tema_macd_state(close, config)
            if np.isnan(tema[i]) or np.isnan(macd[i]) or np.isnan(signal[i]):
                continue

            fresh_buy = tema[i] >= tema[i - 1] and not state_before_bar[i] and macd[i] >= signal[i]

            if not fresh_buy:
                continue

            if i - trend_slope_lookback < 0:
                continue
            trend_ok = (
                close[i] > trend_ema[i] and trend_ema[i] > trend_ema[i - trend_slope_lookback]
            )
            momentum_ok = macd[i] > 0 and signal[i] > 0
            volatility_ok = atr_pct[i] >= min_atr_pct

            if breakout_lookback > 0:
                hh = np.nanmax(high[max(0, i - breakout_lookback) : i])
                breakout_ok = close[i] > hh
            else:
                breakout_ok = True

            if trend_ok and momentum_ok and volatility_ok and breakout_ok:
                buy_list.append(ticker)

        except Exception as e:
            print(ticker, e)

    return buy_list
