from __future__ import annotations

import numpy as np
import pandas as pd

from trading_bot.utility.indicators import ema, rma, sma, true_range


# ---------------------------------------------------------------------------
# 1. Larry Connors RSI(2) & Streak Indicator
# ---------------------------------------------------------------------------
def compute_rsi_2(close: np.ndarray) -> np.ndarray:
    """Calculate ultra-fast 2-period RSI for Larry Connors mean-reversion."""
    n = len(close)
    rsi_arr = np.full(n, np.nan)
    if n < 5:
        return rsi_arr

    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    # 2-period RMA
    alpha = 1.0 / 2.0
    avg_gain = np.zeros(len(delta))
    avg_loss = np.zeros(len(delta))

    avg_gain[0] = gain[0]
    avg_loss[0] = loss[0]
    for i in range(1, len(delta)):
        avg_gain[i] = alpha * gain[i] + (1.0 - alpha) * avg_gain[i - 1]
        avg_loss[i] = alpha * loss[i] + (1.0 - alpha) * avg_loss[i - 1]

    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss == 0, 100.0, avg_gain / avg_loss)
        rsi_val = 100.0 - (100.0 / (1.0 + rs))

    rsi_arr[1:] = rsi_val
    return rsi_arr


# ---------------------------------------------------------------------------
# 2. Kaufman Adaptive Moving Average (KAMA) & Efficiency Ratio
# ---------------------------------------------------------------------------
def compute_kama(
    close: np.ndarray,
    er_length: int = 10,
    fast_period: int = 2,
    slow_period: int = 30,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate Kaufman's Adaptive Moving Average (KAMA) and Efficiency Ratio (ER)."""
    n = len(close)
    kama = np.full(n, np.nan)
    er = np.full(n, np.nan)

    if n < er_length + 2:
        return kama, er

    fast_sc = 2.0 / (fast_period + 1.0)
    slow_sc = 2.0 / (slow_period + 1.0)

    # Calculate absolute daily changes
    abs_diff = np.abs(np.diff(close))
    volatility = pd.Series(abs_diff).rolling(er_length).sum().to_numpy()

    kama[er_length - 1] = close[er_length - 1]

    for i in range(er_length, n):
        change = abs(close[i] - close[i - er_length])
        vol = volatility[i - 1]
        er_val = change / vol if vol > 0 else 0.0
        er[i] = er_val

        # Smoothing constant
        sc = (er_val * (fast_sc - slow_sc) + slow_sc) ** 2
        kama[i] = kama[i - 1] + sc * (close[i] - kama[i - 1])

    return kama, er


# ---------------------------------------------------------------------------
# 3. DonovanWall Range Filter (Volatility Noise Gate)
# ---------------------------------------------------------------------------
def compute_range_filter(
    close: np.ndarray,
    period: int = 20,
    multiplier: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Calculate DonovanWall Range Filter (filter_line, upper_band, lower_band, trend_dir)."""
    n = len(close)
    filt = np.zeros(n)
    up_band = np.zeros(n)
    low_band = np.zeros(n)
    trend = np.zeros(n)  # +1 bull, -1 bear

    if n < period + 5:
        return filt, up_band, low_band, trend

    diff = np.abs(np.diff(close))
    diff_smooth = ema(diff, period)
    r = diff_smooth * multiplier

    filt[0] = close[0]
    for i in range(1, n):
        sm_range = r[i - 1] if i - 1 < len(r) else r[-1]
        prev_filt = filt[i - 1]

        # Upward move beyond range
        if close[i] > prev_filt:
            filt[i] = max(prev_filt, close[i] - sm_range)
        else:
            filt[i] = min(prev_filt, close[i] + sm_range)

        up_band[i] = filt[i] + sm_range
        low_band[i] = filt[i] - sm_range

        # Trend direction
        if filt[i] > prev_filt:
            trend[i] = 1
        elif filt[i] < prev_filt:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]

    return filt, up_band, low_band, trend


# ---------------------------------------------------------------------------
# 4. Non-Repainting Causal Nadaraya-Watson Non-Parametric Kernel Envelope
# ---------------------------------------------------------------------------
def compute_non_repainting_nadaraya_watson(
    close: np.ndarray,
    window: int = 30,
    bandwidth: float = 8.0,
    multiplier: float = 2.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Calculate strictly non-repainting (causal) Gaussian Kernel Regression Envelope."""
    n = len(close)
    kernel_fit = np.full(n, np.nan)
    upper_band = np.full(n, np.nan)
    lower_band = np.full(n, np.nan)

    if n < window:
        return kernel_fit, upper_band, lower_band

    # Precalculate Gaussian weights for lookback offsets 0..window-1
    offsets = np.arange(window, dtype=float)
    weights = np.exp(-(offsets**2) / (2.0 * (bandwidth**2)))
    weight_sum = np.sum(weights)
    norm_weights = weights[::-1] / weight_sum  # Most recent gets highest weight

    # Vectorized convolution across historical causal window
    conv = np.convolve(close, norm_weights, mode="valid")
    kernel_fit[window - 1 :] = conv

    # Calculate rolling Mean Absolute Deviation (MAD)
    abs_dev = np.abs(close - kernel_fit)
    rolling_mad = pd.Series(abs_dev).rolling(window, min_periods=5).mean().to_numpy()

    upper_band = kernel_fit + (multiplier * rolling_mad)
    lower_band = kernel_fit - (multiplier * rolling_mad)

    return kernel_fit, upper_band, lower_band


# ---------------------------------------------------------------------------
# 5. Mark Minervini Stage 2 Trend Template & Volatility Contraction Pattern (VCP)
# ---------------------------------------------------------------------------
def compute_minervini_trend_template(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Calculate Minervini Stage 2 Trend State (is_stage2: bool) and VCP Contraction Ratio."""
    n = len(close)
    is_stage2 = np.zeros(n, dtype=bool)
    vcp_ratio = np.full(n, np.nan)

    if n < 220:
        return is_stage2, vcp_ratio

    sma50 = sma(close, 50)
    sma150 = sma(close, 150)
    sma200 = sma(close, 200)

    # 52-week High and Low (252 bars)
    high_52w = pd.Series(high).rolling(252, min_periods=100).max().to_numpy()
    low_52w = pd.Series(low).rolling(252, min_periods=100).min().to_numpy()

    # Volatility Contraction: ATR(5) vs ATR(20)
    tr = true_range(high, low, close)
    atr5 = rma(tr, 5)
    atr20 = rma(tr, 20)
    with np.errstate(divide="ignore", invalid="ignore"):
        vcp_ratio = atr5 / np.where(atr20 == 0, 1e-6, atr20)

    # 200 SMA slope over last 20 bars
    sma200_slope = np.zeros(n)
    sma200_slope[20:] = sma200[20:] - sma200[:-20]

    for i in range(200, n):
        c = close[i]
        cond_ma = (
            c > sma150[i]
            and c > sma200[i]
            and sma150[i] > sma200[i]
            and sma50[i] > sma150[i]
            and c > sma50[i]
            and sma200_slope[i] >= 0
        )
        cond_52w = (
            (c >= 1.25 * low_52w[i])  # At least 25% above 52w low
            and (c >= 0.75 * high_52w[i])  # Within 25% of 52w high
        )

        is_stage2[i] = cond_ma and cond_52w

    return is_stage2, vcp_ratio
