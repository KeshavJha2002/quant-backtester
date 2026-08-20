from __future__ import annotations

import numpy as np
import pandas as pd

from research.experiments.engine import Trade, simulate_trades
from research.experiments.indicators import (
    compute_adx,
    compute_donchian_channels,
    compute_squeeze_momentum,
    compute_stochastic_oscillator,
)
from trading_bot.projection_cone import (
    ProjectionConeConfig,
    compute_series_entry_sigmas,
)
from trading_bot.tema_macd.strategy import compute_tema_macd_state
from trading_bot.utility.indicators import (
    compute_st_trend_from_config,
    compute_triple_supertrend,
    config,
    ema,
    rsi,
    sma,
)


def align_weekly_to_daily(
    daily_time: pd.Series, weekly_time: pd.Series, weekly_values: np.ndarray
) -> np.ndarray:
    """Merge weekly signal array onto daily timeframe series via backward asof merge."""
    weekly_frame = pd.DataFrame(
        {"time": pd.to_datetime(weekly_time), "w_val": weekly_values}
    ).sort_values("time")
    daily_frame = pd.DataFrame({"time": pd.to_datetime(daily_time)}).sort_values("time")
    aligned = pd.merge_asof(daily_frame, weekly_frame, on="time", direction="backward")
    return aligned["w_val"].to_numpy()


# ---------------------------------------------------------------------------
# STRATEGY 1: Weekly Supertrend Multi-Scale Momentum (Weekly Frame)
# ---------------------------------------------------------------------------
def run_weekly_supertrend_momentum(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(weekly_close) < 30:
        return []

    w_st1 = compute_st_trend_from_config(weekly_close, weekly_high, weekly_low, 10, 2.5, 1)
    w_st2 = compute_st_trend_from_config(weekly_close, weekly_high, weekly_low, 14, 3.5, 2)
    w_rsi = rsi(weekly_close, 14)
    _, _, w_adx = compute_adx(weekly_high, weekly_low, weekly_close, 14)

    n = len(weekly_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        # Entry on Fast ST turning bull while Slow ST is bull, RSI in sweet spot (48-68), and ADX trending (>18)
        buy = bool(
            w_st1[i] == 1
            and w_st1[i - 1] == -1
            and w_st2[i] == 1
            and not np.isnan(w_rsi[i])
            and 46.0 <= w_rsi[i] <= 70.0
            and (np.isnan(w_adx[i]) or w_adx[i] >= 16.0)
        )
        entries[i] = buy

        # Exit when both Supertrends turn bear or Slow ST flips
        if w_st2[i] == -1:
            exits[i] = True

    return simulate_trades(
        weekly_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=3.5,
        slippage_pct=0.20,
        timeframe="W",
    )


# ---------------------------------------------------------------------------
# STRATEGY 2: Weekly TEMA-MACD + Weekly Projection Cone Value (C5 Advanced)
# ---------------------------------------------------------------------------
def run_weekly_tema_macd_cone_value(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()
    weekly_vol = np.asarray(weekly_df["volume"].values, float).ravel()

    if len(weekly_close) < 35:
        return []

    _, _, _, w_before, w_after = compute_tema_macd_state(weekly_close, config)
    w_tema = 3 * (ema(weekly_close, config["tema_len"]) - ema(ema(weekly_close, config["tema_len"]), config["tema_len"])) + ema(ema(ema(weekly_close, config["tema_len"]), config["tema_len"]), config["tema_len"])
    w_macd = ema(weekly_close, config["macd_fast"]) - ema(weekly_close, config["macd_slow"])
    w_sig = sma(w_macd, config["macd_signal"])
    vol_sma = sma(weekly_vol, 10)

    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(weekly_close, weekly_high, weekly_low, "W", cone_config)

    n = len(weekly_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        sigma = sigma_vals[i]
        fresh_buy = bool(
            w_tema[i] >= w_tema[i - 1]
            and not w_before[i]
            and w_macd[i] >= w_sig[i]
        )
        # Value filter: Sigma <= 0.8 (Undervalued or neutral launchpad)
        value_ok = bool(sigma is not None and not np.isnan(sigma) and sigma <= 0.8)
        vol_ok = bool(np.isnan(vol_sma[i]) or weekly_vol[i] >= 0.8 * vol_sma[i])

        if fresh_buy and value_ok and vol_ok:
            entries[i] = True

        # Exit on TEMA/MACD crossunder
        if w_tema[i] < w_tema[i - 1] and w_before[i] and w_macd[i] < w_sig[i]:
            exits[i] = True

    return simulate_trades(
        weekly_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=3.0,
        slippage_pct=0.20,
        entry_sigma_values=sigma_vals,
        timeframe="W",
    )


# ---------------------------------------------------------------------------
# STRATEGY 3: Multi-Timeframe Squeeze Expansion (Weekly Trend + Daily Squeeze)
# ---------------------------------------------------------------------------
def run_mtf_squeeze_expansion(
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

    if len(daily_close) < 50 or len(weekly_close) < 30:
        return []

    # Weekly Macro Regime: Triple Supertrend Bullish
    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    is_squeeze, momentum = compute_squeeze_momentum(daily_high, daily_low, daily_close, 20, 2.0, 20, 1.5)
    daily_rsi = rsi(daily_close, 14)
    sma200 = sma(daily_close, min(200, len(daily_close) // 2))

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(2, n):
        regime_ok = bool(w_bull_on_d[i] and (np.isnan(sma200[i]) or daily_close[i] > sma200[i] * 0.98))
        squeeze_release = bool(
            (is_squeeze[i - 1] or is_squeeze[i - 2])
            and momentum[i] > 0
            and momentum[i] > momentum[i - 1]
        )
        rsi_ok = bool(not np.isnan(daily_rsi[i]) and 50.0 <= daily_rsi[i] <= 72.0)

        if regime_ok and squeeze_release and rsi_ok:
            entries[i] = True

        # Exit on Weekly Bearish Regime or momentum breakdown
        if not w_bull_on_d[i] or (momentum[i] < momentum[i - 1] and momentum[i] < 0):
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=3.2,  # Wide 3.2x ATR trailing stop to ride large trends
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# STRATEGY 4: Dual-Momentum Pullback to 50 EMA Support (MTF Trend Rebound)
# ---------------------------------------------------------------------------
def run_mtf_pullback_ema_rebound(
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

    if len(daily_close) < 60 or len(weekly_close) < 30:
        return []

    # Weekly Macro Trend: Weekly EMA 10 > EMA 30 & Weekly Supertrend Bull
    w_ema10 = ema(weekly_close, 10)
    w_ema30 = ema(weekly_close, 30)
    w_t1, w_t2, _ = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_ema10 >= w_ema30) & ((w_t1 == 1) | (w_t2 == 1))
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    d_ema20 = ema(daily_close, 20)
    d_ema50 = ema(daily_close, 50)
    d_sma200 = sma(daily_close, min(200, len(daily_close) // 2))
    d_rsi = rsi(daily_close, 14)
    stoch_k, stoch_d = compute_stochastic_oscillator(daily_high, daily_low, daily_close, 14, 3)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(2, n):
        regime = bool(
            w_bull_on_d[i]
            and (np.isnan(d_sma200[i]) or daily_close[i] >= d_sma200[i])
            and d_ema20[i] >= d_ema50[i]
        )
        # Pullback into 20-50 EMA zone with RSI in bull support (38-55)
        pullback_zone = bool(
            daily_low[i] <= d_ema20[i] * 1.01
            and daily_close[i] >= d_ema50[i] * 0.97
            and not np.isnan(d_rsi[i])
            and 38.0 <= d_rsi[i] <= 56.0
        )
        # Rebound trigger: Stoch %K crosses above %D and Close > Open
        rebound = bool(
            stoch_k[i] > stoch_d[i]
            and stoch_k[i - 1] <= stoch_d[i - 1]
            and daily_close[i] > daily_close[i - 1]
        )

        if regime and pullback_zone and rebound:
            entries[i] = True

        # Exit when daily close breaks below 50 EMA * 0.95 or weekly turns bear
        if not w_bull_on_d[i] or daily_close[i] < d_ema50[i] * 0.95:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=3.0,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# STRATEGY 5: Weekly Donchian Turtle 2.0 Trend Expansion (Weekly Frame)
# ---------------------------------------------------------------------------
def run_weekly_donchian_turtle(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()
    weekly_vol = np.asarray(weekly_df["volume"].values, float).ravel()

    if len(weekly_close) < 40:
        return []

    w_up_20, _, _ = compute_donchian_channels(weekly_high, weekly_low, 20)
    _, w_low_10, _ = compute_donchian_channels(weekly_high, weekly_low, 10)
    w_ema30 = ema(weekly_close, 30)
    vol_sma = sma(weekly_vol, 10)

    n = len(weekly_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        breakout = bool(weekly_close[i] >= w_up_20[i - 1] and weekly_close[i - 1] < w_up_20[i - 1])
        trend_ok = bool(weekly_close[i] > w_ema30[i])
        vol_ok = bool(np.isnan(vol_sma[i]) or weekly_vol[i] >= 1.05 * vol_sma[i])

        if breakout and trend_ok and vol_ok:
            entries[i] = True

        if weekly_close[i] <= w_low_10[i - 1]:
            exits[i] = True

    return simulate_trades(
        weekly_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=3.2,
        slippage_pct=0.20,
        timeframe="W",
    )


# ---------------------------------------------------------------------------
# STRATEGY 6: Weekly Supertrend + Weekly Projection Cone Value (C6 Advanced)
# ---------------------------------------------------------------------------
def run_weekly_supertrend_cone_value(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(weekly_close) < 35:
        return []

    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)

    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(weekly_close, weekly_high, weekly_low, "W", cone_config)

    n = len(weekly_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        sigma = sigma_vals[i]
        # Fresh weekly bull transition or pullback bounce
        fresh_bull = bool(w_bull[i] and not w_bull[i - 1])
        # Cone value filter: Sigma < 0.5
        value_ok = bool(sigma is not None and not np.isnan(sigma) and sigma <= 0.5)

        if fresh_bull and value_ok:
            entries[i] = True

        # Exit when all 3 Supertrends turn bearish
        if not w_bull[i]:
            exits[i] = True

    return simulate_trades(
        weekly_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=3.5,
        slippage_pct=0.20,
        entry_sigma_values=sigma_vals,
        timeframe="W",
    )
