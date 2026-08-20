from __future__ import annotations

import numpy as np
import pandas as pd

from research.experiments.engine import Trade, simulate_trades
from research.experiments.indicators import (
    compute_adx,
    compute_chandelier_exit,
    compute_donchian_channels,
    compute_hma,
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
# BASELINE 1: TEMA-MACD MTF Baseline (D in W)
# ---------------------------------------------------------------------------
def run_baseline_tema_macd_mtf(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()

    if len(daily_close) < 35 or len(weekly_close) < 35:
        return []

    _, _, _, d_before, _ = compute_tema_macd_state(daily_close, config)
    d_tema = 3 * (ema(daily_close, config["tema_len"]) - ema(ema(daily_close, config["tema_len"]), config["tema_len"])) + ema(ema(ema(daily_close, config["tema_len"]), config["tema_len"]), config["tema_len"])
    d_macd = ema(daily_close, config["macd_fast"]) - ema(daily_close, config["macd_slow"])
    d_sig = sma(d_macd, config["macd_signal"])

    _, _, _, _, w_after = compute_tema_macd_state(weekly_close, config)
    weekly_bull_on_daily = align_weekly_to_daily(
        daily_df["time"], weekly_df["time"], w_after.astype(bool)
    )

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        buy = bool(
            d_tema[i] >= d_tema[i - 1]
            and not d_before[i]
            and d_macd[i] >= d_sig[i]
            and weekly_bull_on_daily[i]
        )
        sell = bool(d_tema[i] < d_tema[i - 1] and d_before[i] and d_macd[i] < d_sig[i])
        entries[i] = buy
        exits[i] = sell

    return simulate_trades(daily_df, entries, exits, ticker=ticker, slippage_pct=0.15)


# ---------------------------------------------------------------------------
# BASELINE 2: Trend Supertrend MTF Baseline (D pullback in W bull)
# ---------------------------------------------------------------------------
def run_baseline_supertrend_mtf(
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

    if len(daily_close) < 25 or len(weekly_close) < 25:
        return []

    d_fast = compute_st_trend_from_config(daily_close, daily_high, daily_low, 10, 3.0, 1)
    d_slow = compute_st_trend_from_config(daily_close, daily_high, daily_low, 14, 3.5, 3)

    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    fast_bear_count = 0
    for i in range(1, n):
        buy = bool(
            d_fast[i - 1] == -1
            and d_fast[i] == 1
            and d_slow[i] == 1
            and w_bull_on_d[i]
        )
        entries[i] = buy

        if d_slow[i] == -1:
            exits[i] = True
            fast_bear_count = 0
        elif d_fast[i] == -1:
            fast_bear_count += 1
            if fast_bear_count >= 2:
                exits[i] = True
        else:
            fast_bear_count = 0

    return simulate_trades(daily_df, entries, exits, ticker=ticker, slippage_pct=0.15)


# ---------------------------------------------------------------------------
# CANDIDATE 1: Squeeze Momentum Breakout (Carter Squeeze + 200 SMA + ADX)
# ---------------------------------------------------------------------------
def run_strategy_squeeze_momentum_breakout(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()

    if len(daily_close) < 50:
        return []

    is_squeeze, momentum = compute_squeeze_momentum(daily_high, daily_low, daily_close, 20, 2.0, 20, 1.5)
    _, _, adx = compute_adx(daily_high, daily_low, daily_close, 14)
    sma200 = sma(daily_close, min(200, len(daily_close) // 2))
    ema50 = ema(daily_close, 50)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(2, n):
        # Squeeze was active recently (1 or 2 bars ago) and momentum is positive and expanding
        was_squeeze = bool(is_squeeze[i - 1] or is_squeeze[i - 2])
        mom_firing = bool(momentum[i] > 0 and momentum[i] > momentum[i - 1])
        trend_bull = bool(daily_close[i] > sma200[i] and daily_close[i] > ema50[i]) if not np.isnan(sma200[i]) else True
        adx_trend = bool(adx[i] >= 18) if not np.isnan(adx[i]) else True

        if was_squeeze and mom_firing and trend_bull and adx_trend:
            entries[i] = True

        # Signal exit when momentum turns down 2 bars in a row or price crosses below 50 EMA
        if (momentum[i] < momentum[i - 1] < momentum[i - 2] and momentum[i] < 0) or (daily_close[i] < ema50[i]):
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.5,  # 2.5x ATR trailing stop
        hard_stop_pct=7.0,     # Max 7% initial stop
        profit_target_pct=25.0, # 25% profit target
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# CANDIDATE 2: MTF Deep Cone Value Pullback + RSI Hook
# ---------------------------------------------------------------------------
def run_strategy_mtf_cone_value_pullback(
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

    if len(daily_close) < 40 or len(weekly_close) < 25:
        return []

    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    weekly_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], weekly_bull)

    rsi_daily = rsi(daily_close, 14)
    stoch_k, stoch_d = compute_stochastic_oscillator(daily_high, daily_low, daily_close, 14, 3)
    sma200 = sma(daily_close, min(200, len(daily_close) // 2))

    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(daily_close, daily_high, daily_low, "D", cone_config)
    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(2, n):
        sigma = sigma_vals[i]

        # Bullish Regime: Weekly Supertrend bull + Price > 200 SMA
        regime_bull = bool(w_bull_on_d[i] and (np.isnan(sma200[i]) or daily_close[i] >= sma200[i] * 0.98))

        # Value Pullback: Cone sigma < -0.5 and RSI in pullback support zone (35-55)
        value_pullback = bool(
            sigma is not None
            and sigma < -0.5
            and not np.isnan(rsi_daily[i])
            and 32.0 <= rsi_daily[i] <= 55.0
        )

        # Trigger: Stoch %K crosses above %D or RSI hooks up
        trigger = bool(
            stoch_k[i] > stoch_d[i]
            and stoch_k[i - 1] <= stoch_d[i - 1]
            and stoch_k[i] < 60.0
        )

        if regime_bull and value_pullback and trigger:
            entries[i] = True

        # Exit when weekly regime turns bearish or daily RSI overbought (>78)
        if not w_bull_on_d[i] or rsi_daily[i] >= 78.0:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.2,
        hard_stop_pct=6.0,
        profit_target_pct=28.0,
        slippage_pct=0.15,
        entry_sigma_values=sigma_vals,
    )


# ---------------------------------------------------------------------------
# CANDIDATE 3: Adaptive Hull & Zero-Lag Trend Engine
# ---------------------------------------------------------------------------
def run_strategy_adaptive_hull_trend(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()
    daily_vol = np.asarray(daily_df["volume"].values, float).ravel()

    if len(daily_close) < 40:
        return []

    hma_fast = compute_hma(daily_close, 9)
    hma_slow = compute_hma(daily_close, 21)
    vol_sma = sma(daily_vol, 20)
    _, _, adx = compute_adx(daily_high, daily_low, daily_close, 14)
    sma200 = sma(daily_close, min(200, len(daily_close) // 2))

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(2, n):
        if np.isnan(hma_fast[i]) or np.isnan(hma_slow[i]):
            continue

        # Fast HMA crosses above Slow HMA + Trend > 200 SMA + Volume Confirmation
        cross_up = bool(hma_fast[i] > hma_slow[i] and hma_fast[i - 1] <= hma_slow[i - 1])
        above_200 = bool(np.isnan(sma200[i]) or daily_close[i] > sma200[i])
        vol_confirm = bool(np.isnan(vol_sma[i]) or daily_vol[i] >= 0.9 * vol_sma[i])
        adx_trend = bool(np.isnan(adx[i]) or adx[i] >= 18)

        if cross_up and above_200 and vol_confirm and adx_trend:
            entries[i] = True

        # Exit on cross under
        if hma_fast[i] < hma_slow[i] and hma_fast[i - 1] >= hma_slow[i - 1]:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.5,
        hard_stop_pct=6.5,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# CANDIDATE 4: Dual Supertrend with Chandelier Exit
# ---------------------------------------------------------------------------
def run_strategy_dual_supertrend_chandelier(
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

    if len(daily_close) < 30 or len(weekly_close) < 20:
        return []

    d_fast = compute_st_trend_from_config(daily_close, daily_high, daily_low, 10, 2.0, 1)
    d_slow = compute_st_trend_from_config(daily_close, daily_high, daily_low, 20, 3.5, 2)
    chandelier_stop = compute_chandelier_exit(daily_high, daily_low, daily_close, 22, 2.8)

    w_t1, w_t2, _ = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        # Entry on Fast ST buy while Slow ST and Weekly are bull
        buy = bool(
            d_fast[i - 1] == -1
            and d_fast[i] == 1
            and d_slow[i] == 1
            and w_bull_on_d[i]
        )
        entries[i] = buy

        # Exit on Chandelier stop violation or Slow ST turn bear
        if (not np.isnan(chandelier_stop[i]) and daily_close[i] < chandelier_stop[i]) or d_slow[i] == -1:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.8,
        hard_stop_pct=7.0,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# CANDIDATE 5: Donchian Turtle Breakout 2.0 with Volatility Scaling
# ---------------------------------------------------------------------------
def run_strategy_donchian_turtle_breakout(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()
    daily_vol = np.asarray(daily_df["volume"].values, float).ravel()

    if len(daily_close) < 40:
        return []

    d_up_20, _, _ = compute_donchian_channels(daily_high, daily_low, 20)
    _, d_low_10, _ = compute_donchian_channels(daily_high, daily_low, 10)
    vol_sma = sma(daily_vol, 20)
    sma200 = sma(daily_close, min(200, len(daily_close) // 2))
    ema50 = ema(daily_close, 50)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        # Breakout above previous 20-day high with volume & macro trend confirmation
        breakout = bool(daily_close[i] >= d_up_20[i - 1] and daily_close[i - 1] < d_up_20[i - 1])
        trend_ok = bool(daily_close[i] > ema50[i] and (np.isnan(sma200[i]) or daily_close[i] > sma200[i]))
        vol_ok = bool(np.isnan(vol_sma[i]) or daily_vol[i] >= 1.1 * vol_sma[i])

        if breakout and trend_ok and vol_ok:
            entries[i] = True

        # Exit on 10-day low breakdown
        if daily_close[i] <= d_low_10[i - 1]:
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.5,
        hard_stop_pct=6.0,
        profit_target_pct=30.0,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# CANDIDATE 6: Enhanced Risk-Managed TEMA-MACD (200 SMA + ATR Stop)
# ---------------------------------------------------------------------------
def run_strategy_enhanced_tema_macd(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()

    if len(daily_close) < 35 or len(weekly_close) < 35:
        return []

    _, _, _, d_before, _ = compute_tema_macd_state(daily_close, config)
    d_tema = 3 * (ema(daily_close, config["tema_len"]) - ema(ema(daily_close, config["tema_len"]), config["tema_len"])) + ema(ema(ema(daily_close, config["tema_len"]), config["tema_len"]), config["tema_len"])
    d_macd = ema(daily_close, config["macd_fast"]) - ema(daily_close, config["macd_slow"])
    d_sig = sma(d_macd, config["macd_signal"])

    _, _, _, _, w_after = compute_tema_macd_state(weekly_close, config)
    weekly_bull_on_daily = align_weekly_to_daily(
        daily_df["time"], weekly_df["time"], w_after.astype(bool)
    )

    sma200 = sma(daily_close, min(200, len(daily_close) // 2))

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(1, n):
        buy = bool(
            d_tema[i] >= d_tema[i - 1]
            and not d_before[i]
            and d_macd[i] >= d_sig[i]
            and weekly_bull_on_daily[i]
            and (np.isnan(sma200[i]) or daily_close[i] > sma200[i])
        )
        sell = bool(d_tema[i] < d_tema[i - 1] and d_before[i] and d_macd[i] < d_sig[i])
        entries[i] = buy
        exits[i] = sell

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.2,
        hard_stop_pct=6.0,
        slippage_pct=0.15,
    )


# ---------------------------------------------------------------------------
# CANDIDATE 7: Triple Confluence Quantum Model (MTF Trend + Cone Value + Squeeze)
# ---------------------------------------------------------------------------
def run_strategy_triple_confluence_quantum(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()
    daily_vol = np.asarray(daily_df["volume"].values, float).ravel()

    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(daily_close) < 45 or len(weekly_close) < 25:
        return []

    # 1. Macro Regime: Weekly Supertrend Bull
    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    # 2. Daily Indicators
    sma200 = sma(daily_close, min(200, len(daily_close) // 2))
    ema20 = ema(daily_close, 20)
    ema50 = ema(daily_close, 50)
    vol_sma = sma(daily_vol, 20)
    rsi_val = rsi(daily_close, 14)
    is_squeeze, momentum = compute_squeeze_momentum(daily_high, daily_low, daily_close, 20, 2.0, 20, 1.5)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(daily_close, daily_high, daily_low, "D", cone_config)
    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    for i in range(2, n):
        sigma = sigma_vals[i]

        # Trend Regime: Weekly Bull + Daily price above or touching 50 EMA / 200 SMA
        trend_ok = bool(
            w_bull_on_d[i]
            and (np.isnan(sma200[i]) or daily_close[i] >= sma200[i] * 0.98)
            and (np.isnan(ema50[i]) or daily_close[i] >= ema50[i] * 0.97)
        )

        # Value Filter: Negative or reasonable Cone Sigma (< 0.2) + RSI not overbought (< 62)
        value_ok = bool(
            sigma is not None
            and sigma <= 0.2
            and not np.isnan(rsi_val[i])
            and 38.0 <= rsi_val[i] <= 62.0
        )

        # Momentum Trigger: Squeeze releasing OR Momentum inflection with price reclaiming EMA 20
        mom_trigger = bool(
            (momentum[i] > momentum[i - 1] and momentum[i] > -0.5)
            and daily_close[i] >= ema20[i]
            and daily_close[i - 1] < ema20[i - 1]
            and (np.isnan(vol_sma[i]) or daily_vol[i] >= 0.85 * vol_sma[i])
        )

        if trend_ok and value_ok and mom_trigger:
            entries[i] = True

        # Signal Exit: Price breaks below 50 EMA & Weekly turns bearish
        if not w_bull_on_d[i] or (daily_close[i] < ema50[i] * 0.96 and momentum[i] < 0):
            exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=2.2,  # 2.2x ATR trailing stop
        hard_stop_pct=5.5,     # Tight 5.5% disaster stop
        profit_target_pct=26.0, # 26% Target scaling
        slippage_pct=0.15,
        entry_sigma_values=sigma_vals,
    )
