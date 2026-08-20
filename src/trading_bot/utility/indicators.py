from __future__ import annotations

import numpy as np
import pandas as pd

# Global Default Parameters
config: dict[str, int] = {
    "tema_len": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
}

st_config: dict[str, int | float] = {
    "atr_len": 14,
    "atr_mult": 3.0,
    "atr_smooth": 2,
}


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Calculate True Range across high, low, and close arrays."""
    high = np.asarray(high, dtype=float).ravel()
    low = np.asarray(low, dtype=float).ravel()
    close = np.asarray(close, dtype=float).ravel()

    n = len(close)
    if n == 0:
        return np.array([], dtype=float)

    tr = np.full(n, np.nan, dtype=float)
    tr[0] = high[0] - low[0]
    if n > 1:
        hl = high[1:] - low[1:]
        hc = np.abs(high[1:] - close[:-1])
        lc = np.abs(low[1:] - close[:-1])
        tr[1:] = np.maximum(hl, np.maximum(hc, lc))

    return tr


def rma(series: np.ndarray, length: int) -> np.ndarray:
    """Calculate Wilder's Exponential Moving Average (RMA)."""
    series = np.asarray(series, dtype=float).ravel()
    n = len(series)
    out = np.full(n, np.nan, dtype=float)
    if length <= 0 or n == 0:
        return out

    alpha = 1.0 / float(length)
    valid = np.where(~np.isnan(series))[0]
    if len(valid) < length:
        return out

    start = valid[length - 1]
    out[start] = float(np.mean(series[valid[:length]]))

    for i in range(start + 1, n):
        out[i] = (
            out[i - 1]
            if np.isnan(series[i])
            else out[i - 1] + alpha * (series[i] - out[i - 1])
        )

    return out


def sma(series: np.ndarray, length: int) -> np.ndarray:
    """Calculate Simple Moving Average (SMA)."""
    series = np.asarray(series, dtype=float).ravel()
    n = len(series)
    out = np.full(n, np.nan, dtype=float)
    if length <= 0 or n == 0 or n < length:
        return out

    for i in range(length - 1, n):
        window = series[i - length + 1 : i + 1]
        if not np.isnan(window).any():
            out[i] = float(window.mean())

    return out


def ema(candle_close: np.ndarray, length: int) -> np.ndarray:
    """Calculate Exponential Moving Average (EMA)."""
    candle_close = np.asarray(candle_close, dtype=float).ravel()
    n = len(candle_close)
    out = np.full(n, np.nan, dtype=float)
    if length <= 0 or n == 0:
        return out

    alpha = 2.0 / (float(length) + 1.0)
    valid = np.where(~np.isnan(candle_close))[0]
    if len(valid) < length:
        return out

    start = valid[length - 1]
    out[start] = float(candle_close[valid[:length]].mean())

    for i in range(start + 1, n):
        out[i] = (
            out[i - 1]
            if np.isnan(candle_close[i])
            else (alpha * candle_close[i] + (1.0 - alpha) * out[i - 1])
        )

    return out


def rsi(data: pd.DataFrame | np.ndarray, length: int = 14) -> np.ndarray:
    """Calculate Relative Strength Index (RSI)."""
    if isinstance(data, pd.DataFrame):
        close = np.asarray(data["close"].values, dtype=float).ravel()
    else:
        close = np.asarray(data, dtype=float).ravel()

    if len(close) == 0:
        return np.array([], dtype=float)

    delta = np.diff(close, prepend=np.nan)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, np.nan)
        rsi_out = np.where(
            avg_loss == 0,
            np.where(avg_gain > 0, 100.0, 50.0),
            100.0 - (100.0 / (1.0 + rs)),
        )

    return rsi_out


def compute_st_trend_from_config(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr_len: int,
    atr_mult: float,
    smooth_len: int,
) -> np.ndarray:
    """Compute Supertrend trend direction series (+1 for bullish, -1 for bearish, 0 for uninitialized)."""
    close = np.asarray(close, dtype=float).ravel()
    high = np.asarray(high, dtype=float).ravel()
    low = np.asarray(low, dtype=float).ravel()

    n = len(close)
    trend = np.zeros(n, dtype=int)
    if n == 0:
        return trend

    source = ema(close, smooth_len) if smooth_len > 1 else close
    tr = true_range(high, low, close)
    atr = rma(tr, atr_len) * atr_mult

    supertrend = np.full(n, np.nan, dtype=float)
    start = None

    for i in range(n):
        if not np.isnan(source[i]) and not np.isnan(atr[i]):
            supertrend[i] = source[i] - atr[i]
            trend[i] = 1
            start = i
            break

    if start is None:
        return trend

    for i in range(start + 1, n):
        if np.isnan(source[i]) or np.isnan(atr[i]):
            supertrend[i] = supertrend[i - 1]
            trend[i] = trend[i - 1]
            continue

        if trend[i - 1] == 1:
            if source[i] < supertrend[i - 1]:
                trend[i] = -1
                supertrend[i] = source[i] + atr[i]
            else:
                trend[i] = 1
                supertrend[i] = max(supertrend[i - 1], source[i] - atr[i])
        else:
            if source[i] > supertrend[i - 1]:
                trend[i] = 1
                supertrend[i] = source[i] - atr[i]
            else:
                trend[i] = -1
                supertrend[i] = min(supertrend[i - 1], source[i] + atr[i])

    return trend


def compute_triple_supertrend(
    close: np.ndarray, high: np.ndarray, low: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the 3 standard Supertrend regime series used across the strategies."""
    trend1 = compute_st_trend_from_config(close, high, low, atr_len=10, atr_mult=3.0, smooth_len=1)
    trend2 = compute_st_trend_from_config(close, high, low, atr_len=14, atr_mult=3.0, smooth_len=2)
    trend3 = compute_st_trend_from_config(close, high, low, atr_len=14, atr_mult=3.5, smooth_len=3)
    return trend1, trend2, trend3
