from __future__ import annotations

import numpy as np
import pandas as pd

from research.experiments.advanced_quant_indicators import (
    compute_kama,
    compute_minervini_trend_template,
    compute_non_repainting_nadaraya_watson,
    compute_range_filter,
    compute_rsi_2,
)
from research.experiments.engine import Trade, simulate_trades
from research.experiments.indicators import compute_adx
from research.experiments.strategies import align_weekly_to_daily
from trading_bot.projection_cone import (
    ProjectionConeConfig,
    compute_series_entry_sigmas,
)
from trading_bot.utility.indicators import (
    compute_triple_supertrend,
    sma,
)


# ---------------------------------------------------------------------------
# Q1: Classic Larry Connors RSI(2) Mean Reversion (Above 200 SMA)
# ---------------------------------------------------------------------------
def run_connors_rsi2_mean_reversion(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()

    if len(daily_close) < 210:
        return []

    rsi2 = compute_rsi_2(daily_close)
    sma200 = sma(daily_close, 200)
    sma5 = sma(daily_close, 5)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(200, n):
        # Long only when Price > 200 SMA and RSI(2) drops below 10 (extreme oversold dip)
        if daily_close[i] > sma200[i] and not np.isnan(rsi2[i]) and rsi2[i] <= 10.0:
            entries[i] = True

        # Exit when price recovers above 5-day SMA or RSI(2) recovers above 70
        if daily_close[i] >= sma5[i] or rsi2[i] >= 70.0:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        hard_stop_pct=6.0,  # 6% disaster stop
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q2: Connors RSI(2) + Projection Cone Deep Value Hybrid
# ---------------------------------------------------------------------------
def run_connors_rsi2_cone_hybrid(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()

    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(daily_close) < 210 or len(weekly_close) < 25:
        return []

    # Weekly Macro Regime: Triple Supertrend Bull
    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    rsi2 = compute_rsi_2(daily_close)
    sma200 = sma(daily_close, 200)
    sma5 = sma(daily_close, 5)

    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(daily_close, daily_high, daily_low, "D", cone_config)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(200, n):
        sigma = sigma_vals[i]
        regime_ok = bool(w_bull_on_d[i] and daily_close[i] > sma200[i])
        cone_value = bool(sigma is not None and not np.isnan(sigma) and sigma <= -0.4)
        rsi_oversold = bool(not np.isnan(rsi2[i]) and rsi2[i] <= 12.0)

        if regime_ok and cone_value and rsi_oversold:
            entries[i] = True

        if daily_close[i] >= sma5[i] or rsi2[i] >= 65.0:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        hard_stop_pct=5.5,
        entry_sigma_values=sigma_vals,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q3: Double 7s Mean Reversion in 200 SMA Bull Trend
# ---------------------------------------------------------------------------
def run_double_7s_mean_reversion(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()

    if len(daily_close) < 210:
        return []

    sma200 = sma(daily_close, 200)
    lowest_7 = pd.Series(daily_close).rolling(7).min().to_numpy()
    highest_7 = pd.Series(daily_close).rolling(7).max().to_numpy()

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(200, n):
        # Buy on 7-day low when price > 200 SMA
        if daily_close[i] > sma200[i] and daily_close[i] <= lowest_7[i]:
            entries[i] = True

        # Exit on 7-day high
        if daily_close[i] >= highest_7[i]:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        hard_stop_pct=6.5,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q4: Mark Minervini Stage 2 Trend Template + VCP Breakout
# ---------------------------------------------------------------------------
def run_minervini_vcp_breakout(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()
    daily_vol = np.asarray(daily_df["volume"].values, float).ravel()

    if len(daily_close) < 260:
        return []

    is_stage2, vcp_ratio = compute_minervini_trend_template(daily_high, daily_low, daily_close)
    vol_sma = sma(daily_vol, 20)
    sma50 = sma(daily_close, 50)
    high_20 = pd.Series(daily_high).rolling(20).max().to_numpy()

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(252, n):
        # Stage 2 Uptrend + Volatility Contraction (ATR compression) + 20-day high breakout with volume surge
        breakout = bool(daily_close[i] >= high_20[i - 1] and daily_close[i - 1] < high_20[i - 1])
        vol_surge = bool(not np.isnan(vol_sma[i]) and daily_vol[i] >= 1.25 * vol_sma[i])
        vcp_compressed = bool(not np.isnan(vcp_ratio[i]) and vcp_ratio[i] <= 0.85)

        if is_stage2[i] and breakout and vol_surge and vcp_compressed:
            entries[i] = True

        # Exit on 50 SMA breakdown
        if daily_close[i] < sma50[i]:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.5,
        hard_stop_pct=6.0,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q5: Kaufman Adaptive Moving Average (KAMA) + Efficiency Ratio Filter
# ---------------------------------------------------------------------------
def run_kaufman_adaptive_trend(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()

    if len(daily_close) < 210:
        return []

    kama, er = compute_kama(daily_close, er_length=10, fast_period=2, slow_period=30)
    sma200 = sma(daily_close, 200)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(200, n):
        if np.isnan(kama[i]) or np.isnan(er[i]):
            continue

        # Buy when price crosses above KAMA with high Efficiency Ratio (> 0.35 indicates strong trend efficiency)
        cross_above = bool(daily_close[i] > kama[i] and daily_close[i - 1] <= kama[i - 1])
        trend_efficient = bool(er[i] >= 0.32 and daily_close[i] > sma200[i])

        if cross_above and trend_efficient:
            entries[i] = True

        # Exit when price crosses below KAMA
        if daily_close[i] < kama[i]:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.8,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q6: DonovanWall Range Filter Momentum Engine
# ---------------------------------------------------------------------------
def run_donovanwall_range_filter(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()

    if len(daily_close) < 210:
        return []

    filt, _, _, trend = compute_range_filter(daily_close, period=20, multiplier=2.0)
    _, _, adx = compute_adx(daily_high, daily_low, daily_close, 14)
    sma200 = sma(daily_close, 200)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(200, n):
        # Range Filter flips to Bullish + Price > 200 SMA + ADX >= 18
        trend_flip_bull = bool(trend[i] == 1 and trend[i - 1] == -1)
        above_200 = bool(daily_close[i] > sma200[i])
        adx_ok = bool(not np.isnan(adx[i]) and adx[i] >= 18.0)

        if trend_flip_bull and above_200 and adx_ok:
            entries[i] = True

        if trend[i] == -1:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.8,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q7: Non-Repainting Nadaraya-Watson Kernel Mean Reversion
# ---------------------------------------------------------------------------
def run_nadaraya_watson_envelope_bounce(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()

    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(daily_close) < 210 or len(weekly_close) < 25:
        return []

    # Weekly Macro Regime
    w_t1, w_t2, _ = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    kernel_fit, upper_b, lower_b = compute_non_repainting_nadaraya_watson(daily_close, window=30, bandwidth=8.0, multiplier=2.0)
    sma200 = sma(daily_close, 200)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(200, n):
        if np.isnan(lower_b[i]) or np.isnan(upper_b[i]):
            continue

        # Price touches or dips below lower kernel band in weekly bull regime, then bounces (close > open)
        oversold_bounce = bool(
            daily_low[i] <= lower_b[i]
            and daily_close[i] > daily_df["open"].iloc[i]
            and w_bull_on_d[i]
            and daily_close[i] > sma200[i]
        )

        if oversold_bounce:
            entries[i] = True

        # Exit when price reaches kernel fit center line or upper band
        if daily_close[i] >= kernel_fit[i] * 1.02 or daily_close[i] >= upper_b[i]:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        hard_stop_pct=5.5,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# Q8: Ultra High-Win-Rate Confluence Model (Minervini Stage 2 + Connors RSI(2) Dip)
# ---------------------------------------------------------------------------
def run_ultra_high_wr_stage2_connors_hybrid(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()

    if len(daily_close) < 260:
        return []

    is_stage2, _ = compute_minervini_trend_template(daily_high, daily_low, daily_close)
    rsi2 = compute_rsi_2(daily_close)
    sma5 = sma(daily_close, 5)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(252, n):
        # Stock is in confirmed Minervini Stage 2 uptrend and experiences an ultra-short-term RSI(2) panic dip (<= 15)
        if is_stage2[i] and not np.isnan(rsi2[i]) and rsi2[i] <= 15.0:
            entries[i] = True

        # Mean-reversion exit when price recovers above 5-day SMA or RSI(2) > 65
        if daily_close[i] >= sma5[i] or rsi2[i] >= 65.0:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        hard_stop_pct=5.0,  # 5% disaster stop
        slippage_pct=0.15,
    )
