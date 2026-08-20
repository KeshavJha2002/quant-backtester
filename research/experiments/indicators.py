from __future__ import annotations

import numpy as np
import pandas as pd

from trading_bot.utility.indicators import ema, rma, sma, true_range


def compute_adx(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    length: int = 14,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate +DI, -DI, and ADX."""
    n = len(close)
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    adx = np.full(n, np.nan)

    if n < length * 2:
        return plus_di, minus_di, adx

    up_move = np.zeros(n)
    down_move = np.zeros(n)
    up_move[1:] = high[1:] - high[:-1]
    down_move[1:] = low[:-1] - low[1:]

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr = true_range(high, low, close)
    tr_smooth = rma(tr, length)
    plus_dm_smooth = rma(plus_dm, length)
    minus_dm_smooth = rma(minus_dm, length)

    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100.0 * (plus_dm_smooth / tr_smooth)
        minus_di = 100.0 * (minus_dm_smooth / tr_smooth)
        dx_denom = plus_di + minus_di
        dx = np.where(dx_denom > 0, 100.0 * np.abs(plus_di - minus_di) / dx_denom, 0.0)

    adx = rma(dx, length)
    return plus_di, minus_di, adx


def compute_keltner_channels(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    length: int = 20,
    multiplier: float = 1.5,
    atr_length: int = 10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate Keltner Channels (Mid, Upper, Lower)."""
    mid = ema(close, length)
    tr = true_range(high, low, close)
    atr = rma(tr, atr_length)
    upper = mid + (multiplier * atr)
    lower = mid - (multiplier * atr)
    return mid, upper, lower


def compute_bollinger_bands(
    close: np.ndarray,
    length: int = 20,
    multiplier: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate Bollinger Bands (Mid, Upper, Lower)."""
    n = len(close)
    mid = sma(close, length)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    if n >= length:
        rolling_std = pd.Series(close).rolling(length).std(ddof=0).to_numpy()
        upper = mid + (multiplier * rolling_std)
        lower = mid - (multiplier * rolling_std)

    return mid, upper, lower


def compute_squeeze_momentum(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    bb_length: int = 20,
    bb_mult: float = 2.0,
    kc_length: int = 20,
    kc_mult: float = 1.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate John Carter's Squeeze State (is_squeeze: bool) and Momentum value."""
    n = len(close)
    is_squeeze = np.zeros(n, dtype=bool)
    momentum = np.zeros(n)

    if n < max(bb_length, kc_length):
        return is_squeeze, momentum

    _, bb_up, bb_low = compute_bollinger_bands(close, bb_length, bb_mult)
    _, kc_up, kc_low = compute_keltner_channels(high, low, close, kc_length, kc_mult)

    # Squeeze is on when BB is inside KC
    is_squeeze = (bb_low > kc_low) & (bb_up < kc_up)

    # Momentum: delta between close and average of (Donchian mid + SMA)
    highest = pd.Series(high).rolling(kc_length).max().to_numpy()
    lowest = pd.Series(low).rolling(kc_length).min().to_numpy()
    mid_donchian = (highest + lowest) / 2.0
    mid_sma = sma(close, kc_length)
    basis = (mid_donchian + mid_sma) / 2.0
    delta = close - basis

    # Linear regression slope approximation (using EMA of delta)
    momentum = ema(delta, 12)
    return is_squeeze, momentum


def compute_hma(close: np.ndarray, length: int = 16) -> np.ndarray:
    """Calculate Hull Moving Average (HMA = WMA(2*WMA(n/2) - WMA(n)), sqrt(n))."""
    n = len(close)
    if n < length + 5:
        return np.full(n, np.nan)

    def _wma(series: np.ndarray, w: int) -> np.ndarray:
        if len(series) < w:
            return np.full(len(series), np.nan)
        weights = np.arange(1, w + 1, dtype=float)
        w_sum = weights.sum()
        conv = np.convolve(series, weights[::-1] / w_sum, mode="valid")
        out = np.full(len(series), np.nan)
        out[w - 1 :] = conv
        return out

    half_len = max(1, length // 2)
    sqrt_len = max(1, int(np.sqrt(length)))

    wma_half = _wma(close, half_len)
    wma_full = _wma(close, length)
    diff = 2.0 * wma_half - wma_full

    valid_idx = np.where(~np.isnan(diff))[0]
    if len(valid_idx) == 0:
        return np.full(n, np.nan)

    first_valid = valid_idx[0]
    hma_arr = np.full(n, np.nan)
    sub_diff = diff[first_valid:]
    sub_hma = _wma(sub_diff, sqrt_len)
    hma_arr[first_valid:] = sub_hma
    return hma_arr


def compute_stochastic_oscillator(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    k_length: int = 14,
    d_length: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate Fast Stochastic (%K, %D)."""
    highest = pd.Series(high).rolling(k_length).max().to_numpy()
    lowest = pd.Series(low).rolling(k_length).min().to_numpy()
    range_hl = highest - lowest
    range_hl = np.where(range_hl == 0, 1e-8, range_hl)
    percent_k = 100.0 * (close - lowest) / range_hl
    percent_d = sma(percent_k, d_length)
    return percent_k, percent_d


def compute_chandelier_exit(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    length: int = 22,
    multiplier: float = 3.0,
) -> np.ndarray:
    """Calculate Chandelier Exit Long Stop (Highest High - multiplier * ATR)."""
    tr = true_range(high, low, close)
    atr = rma(tr, length)
    highest_high = pd.Series(high).rolling(length).max().to_numpy()
    return highest_high - (multiplier * atr)


def compute_donchian_channels(
    high: np.ndarray,
    low: np.ndarray,
    length: int = 20,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate Donchian Channels (Upper, Lower, Mid)."""
    upper = pd.Series(high).rolling(length).max().to_numpy()
    lower = pd.Series(low).rolling(length).min().to_numpy()
    mid = (upper + lower) / 2.0
    return upper, lower, mid
