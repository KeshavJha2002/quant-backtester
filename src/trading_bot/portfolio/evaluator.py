from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.portfolio.models import Position, PositionEvaluation
from trading_bot.portfolio.reasoning import analyze_structural_patterns
from trading_bot.projection_cone import (
    ProjectionConeConfig,
    calculate_sigma_move,
    find_last_pivot,
    resolve_bars_per_year,
)
from trading_bot.utility.indicators import (
    compute_st_trend_from_config,
    compute_triple_supertrend,
    rma,
    sma,
    true_range,
)


def _compute_adx(high: np.ndarray, low: np.ndarray, close: np.ndarray, length: int = 14) -> float:
    n = len(close)
    if n < length * 2:
        return 20.0

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

    adx_arr = rma(dx, length)
    return float(adx_arr[-1]) if not np.isnan(adx_arr[-1]) else 20.0


def evaluate_position(
    position: Position,
    fetcher: Any,
    complete_fetcher: Any,
    cone_config: ProjectionConeConfig | None = None,
) -> PositionEvaluation:
    ticker = position.ticker
    cfg = cone_config or ProjectionConeConfig(lock_mode=True, lock_to_bull=False)

    try:
        d_df = complete_fetcher(ticker, type="D")
        w_df = fetcher(ticker, type="W")

        d_close = np.asarray(d_df["close"].values, float).ravel()
        d_high = np.asarray(d_df["high"].values, float).ravel()
        d_low = np.asarray(d_df["low"].values, float).ravel()
        n = len(d_close)

        w_close = np.asarray(w_df["close"].values, float).ravel()
        w_high = np.asarray(w_df["high"].values, float).ravel()
        w_low = np.asarray(w_df["low"].values, float).ravel()

        curr_price = float(d_close[-1])
        invested_val = position.quantity * position.avg_buy_price
        current_val = position.quantity * curr_price
        pnl_amt = current_val - invested_val
        pnl_pct = ((curr_price - position.avg_buy_price) / position.avg_buy_price) * 100.0 if position.avg_buy_price > 0 else 0.0

        # Holding duration
        try:
            buy_dt = datetime.strptime(position.buy_date, "%Y-%m-%d").date()
            holding_days = (date.today() - buy_dt).days
        except Exception:
            holding_days = 0

        # 1. Technical Indicators
        w_t1, w_t2, w_t3 = compute_triple_supertrend(w_close, w_high, w_low)
        weekly_bull = bool(w_t1[-1] == 1 or w_t2[-1] == 1 or w_t3[-1] == 1)

        d_fast = compute_st_trend_from_config(d_close, d_high, d_low, 10, 3.0, 1)
        d_slow = compute_st_trend_from_config(d_close, d_high, d_low, 14, 3.5, 3)
        daily_st_bull = bool(d_slow[-1] == 1)

        sma200 = float(sma(d_close, min(200, n // 2))[-1])
        above_200 = bool(np.isnan(sma200) or curr_price >= sma200 * 0.98)

        adx_val = _compute_adx(d_high, d_low, d_close, 14)

        # 2. Projection Cone Sigma Move
        bars_per_year = resolve_bars_per_year("D", cfg.bars_per_year)
        vol_series = pd.Series(np.log(d_close[1:] / d_close[:-1])).rolling(cfg.vol_length).std() * np.sqrt(bars_per_year)
        current_vol = float(vol_series.iloc[-1]) if len(vol_series) > 0 else 0.30

        pivot_idx = find_last_pivot(d_high, d_low, cfg.pivot_len, cfg.lock_to_bull)
        anchor_idx = pivot_idx if (cfg.lock_mode and pivot_idx is not None) else (n - 1)
        anchor_price = float(d_low[anchor_idx] if cfg.lock_to_bull else d_high[anchor_idx]) if pivot_idx is not None else curr_price
        bars_since = max(n - 1 - anchor_idx, 1)

        sigma_move = calculate_sigma_move(
            current_price=curr_price,
            anchor_price=anchor_price,
            current_vol=current_vol if (not np.isnan(current_vol) and current_vol > 0) else 0.30,
            bars_since_anchor=bars_since,
            bars_per_year=bars_per_year,
        )

        # 3. Dynamic Stop Loss & Target Calculation
        # Suggested stop loss = max(Slow Supertrend Floor, 6% Disaster Stop, Break-even if PnL > 10%)
        tr = true_range(d_high, d_low, d_close)
        atr14 = float(rma(tr, 14)[-1])
        suggested_stop = max(curr_price - (2.5 * atr14), position.avg_buy_price * 0.94)
        if pnl_pct >= 12.0:
            suggested_stop = max(suggested_stop, position.avg_buy_price * 1.02)  # Lock in profits at breakeven+

        # Target price: +2.0σ Upper Projection Cone boundary
        expected_drift = np.sqrt(bars_since / bars_per_year) * (current_vol if current_vol > 0 else 0.30)
        suggested_target = anchor_price * (1.0 + (2.0 * expected_drift))

        # Risk-reward ratio
        downside = max(1.0, curr_price - suggested_stop)
        upside = max(1.0, suggested_target - curr_price)
        rr_ratio = upside / downside

        # 4. Structural Pattern Analysis
        patterns = analyze_structural_patterns(d_df, w_df, ticker, sigma_move=sigma_move)

        # 5. 4-State Decision Logic
        action: str
        action_color: str
        reasoning: str
        details: list[str] = []

        # Decision Rule 1: EXIT
        if not weekly_bull and d_slow[-1] == -1:
            action = "EXIT"
            action_color = "red"
            reasoning = "🔴 EXIT: Both Weekly and Daily Supertrends are Bearish. Trend structure is broken. Cut loss / exit to preserve capital."
            details.append("Weekly macro trend broken (Triple Supertrend all Bearish).")
            details.append("Daily slow Supertrend confirmed Bearish.")
        elif d_slow[-1] == -1 and (n >= 3 and d_fast[-1] == -1 and d_fast[-2] == -1):
            action = "EXIT"
            action_color = "red"
            reasoning = "🔴 EXIT: 2-Bar Daily Supertrend breakdown triggered. Protect profits/capital."
            details.append("Daily fast Supertrend has been red for >= 2 consecutive bars.")

        # Decision Rule 2: TRIM / TAKE PROFIT
        elif sigma_move >= 1.9 or (pnl_pct >= 25.0 and sigma_move >= 1.5):
            action = "TRIM"
            action_color = "orange"
            reasoning = f"🟡 TRIM (Take Profit): Price extended to +{sigma_move:.2f}σ near upper Projection Cone boundary. Lock in 30%-50% profits."
            details.append(f"Price is in Upper Resistance Zone (+{sigma_move:.2f}σ). Mean-reversion pullback probable.")
            details.append(f"Unrealized P&L is strong ({pnl_pct:+.1f}%). Safe point to lock gains.")

        # Decision Rule 3: ADD / PYRAMID (Build Better Position)
        elif (
            weekly_bull
            and above_200
            and sigma_move <= 0.0
            and d_fast[-1] == 1
            and pnl_pct >= 0.0  # Only pyramid winning positions
            and position.pyramid_count < 3
        ):
            action = "ADD"
            action_color = "green"
            reasoning = f"🟢 ADD / PYRAMID: Stock pulled back to Discount Zone ({sigma_move:+.2f}σ) inside Weekly Bull trend. Excellent low-risk spot to add 0.5-1.0 unit."
            details.append("Weekly macro trend is strong and Bullish.")
            details.append(f"Valuation is in discount ({sigma_move:+.2f}σ).")
            details.append("Daily fast Supertrend just flipped green.")

        # Decision Rule 4: HOLD
        else:
            action = "HOLD"
            action_color = "blue"
            reasoning = f"⚪ HOLD: Macro trend is healthy (Weekly Bull: {weekly_bull}), position is within normal operating range ({sigma_move:+.2f}σ). Let winner run."
            details.append(f"Price is within normal trend range ({sigma_move:+.2f}σ).")
            details.append(f"Current P&L is {pnl_pct:+.1f}%. Trailing stop set at ₹{suggested_stop:,.2f}.")

        details.extend(patterns.key_strengths)
        details.extend(patterns.key_risks)

        health_score = patterns.structural_score
        if not weekly_bull:
            health_score -= 25.0
        if d_slow[-1] == -1:
            health_score -= 20.0
        health_score = float(np.clip(health_score, 5.0, 98.0))

        return PositionEvaluation(
            ticker=ticker,
            quantity=position.quantity,
            avg_buy_price=position.avg_buy_price,
            current_price=curr_price,
            invested_value=invested_val,
            current_value=current_val,
            pnl_amount=pnl_amt,
            pnl_percent=pnl_pct,
            holding_days=holding_days,
            daily_sigma=sigma_move,
            weekly_bull=weekly_bull,
            daily_st_bull=daily_st_bull,
            above_200_sma=above_200,
            adx_value=adx_val,
            action=action,
            action_color=action_color,
            suggested_stop_loss=suggested_stop,
            suggested_target_price=suggested_target,
            risk_reward_ratio=rr_ratio,
            health_score=health_score,
            reasoning_summary=reasoning,
            structural_details=details,
        )

    except Exception as exc:
        return PositionEvaluation(
            ticker=ticker,
            quantity=position.quantity,
            avg_buy_price=position.avg_buy_price,
            current_price=position.avg_buy_price,
            invested_value=position.quantity * position.avg_buy_price,
            current_value=position.quantity * position.avg_buy_price,
            pnl_amount=0.0,
            pnl_percent=0.0,
            holding_days=0,
            daily_sigma=0.0,
            weekly_bull=True,
            daily_st_bull=True,
            above_200_sma=True,
            adx_value=20.0,
            action="HOLD",
            action_color="blue",
            suggested_stop_loss=position.avg_buy_price * 0.94,
            suggested_target_price=position.avg_buy_price * 1.25,
            risk_reward_ratio=2.0,
            health_score=50.0,
            reasoning_summary=f"⚠️ Live market data fetch pending or ticker unavailable ({exc}). Maintain position.",
            structural_details=[f"Error: {exc}"],
        )
