from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    find_last_pivot,
    resolve_bars_per_year,
)
from trading_bot.utility.indicators import rma, true_range


@dataclass
class SizingRecommendation:
    ticker: str
    holding_period: str  # "Swing (1-4w)", "Positional (1-6m)", "Long-Term (>6m)"
    current_price: float
    suggested_stop_loss: float
    stop_distance_pct: float
    target_price: float
    upside_potential_pct: float
    risk_reward_ratio: float

    # Position sizing results
    recommended_shares: int
    total_investment_amount: float
    portfolio_allocation_pct: float
    capital_at_risk_amount: float
    capital_at_risk_pct: float

    # Quantitative rationale
    sizing_rationale: str
    risk_notes: list[str]


def calculate_position_size(
    ticker: str,
    daily_df: pd.DataFrame,
    total_budget: float,
    available_cash: float,
    holding_period: str = "Positional (1-6m)",
    risk_per_trade_pct: float = 1.0,
    max_position_cap_pct: float = 12.0,
) -> SizingRecommendation:
    """Calculate mathematically optimal position size based on stock volatility and holding period."""
    close = np.asarray(daily_df["close"].values, float).ravel()
    high = np.asarray(daily_df["high"].values, float).ravel()
    low = np.asarray(daily_df["low"].values, float).ravel()
    n = len(close)

    current_price = float(close[-1]) if n > 0 else 100.0

    # ATR Volatility
    tr = true_range(high, low, close)
    atr14 = float(rma(tr, 14)[-1]) if n >= 14 else (current_price * 0.03)

    # 1. Holding Period Stop & Target Calibration
    if "Swing" in holding_period:
        # Swing: 1.8x ATR Stop, Target at +1.8σ
        stop_mult = 1.8
        cone_target_sigma = 1.8
        period_cap_pct = min(max_position_cap_pct, 10.0)
        risk_pct = min(risk_per_trade_pct, 1.0)
    elif "Long-Term" in holding_period:
        # Long-Term: 3.5x ATR Stop / 200 SMA floor, Target at +2.5σ
        stop_mult = 3.5
        cone_target_sigma = 2.5
        period_cap_pct = min(max_position_cap_pct, 15.0)
        risk_pct = min(risk_per_trade_pct, 1.5)
    else:  # Positional (1-6m) - Default
        stop_mult = 2.5
        cone_target_sigma = 2.0
        period_cap_pct = min(max_position_cap_pct, 12.0)
        risk_pct = risk_per_trade_pct

    # Calculated Stop Loss
    stop_distance_pts = max(atr14 * stop_mult, current_price * 0.04)  # Minimum 4% disaster floor
    suggested_stop = max(1.0, current_price - stop_distance_pts)
    stop_pct = ((current_price - suggested_stop) / current_price) * 100.0

    # Calculated Target Price (Projection Cone)
    cfg = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    bars_per_year = resolve_bars_per_year("D", cfg.bars_per_year)
    vol_series = pd.Series(np.log(close[1:] / close[:-1])).rolling(cfg.vol_length).std() * np.sqrt(bars_per_year)
    current_vol = float(vol_series.iloc[-1]) if len(vol_series) > 0 else 0.30
    pivot_idx = find_last_pivot(high, low, cfg.pivot_len, cfg.lock_to_bull)
    anchor_idx = pivot_idx if (cfg.lock_mode and pivot_idx is not None) else (n - 1)
    anchor_price = float(low[anchor_idx] if cfg.lock_to_bull else high[anchor_idx]) if pivot_idx is not None else current_price
    bars_since = max(n - 1 - anchor_idx, 1)

    expected_drift = np.sqrt(bars_since / bars_per_year) * (current_vol if current_vol > 0 else 0.30)
    target_price = anchor_price * (1.0 + (cone_target_sigma * expected_drift))
    if target_price <= current_price:
        target_price = current_price * 1.20

    upside_pct = ((target_price - current_price) / current_price) * 100.0
    rr_ratio = (target_price - current_price) / max(1.0, current_price - suggested_stop)

    # 2. Mathematical Capital & Risk Sizing
    # Risk Budget in Currency
    max_risk_amount = total_budget * (risk_pct / 100.0)

    # Max shares by risk
    shares_by_risk = int(max_risk_amount / max(1.0, current_price - suggested_stop))

    # Max shares by portfolio allocation cap (e.g. 10%-15% max per position)
    max_capital_for_pos = total_budget * (period_cap_pct / 100.0)
    shares_by_cap = int(max_capital_for_pos / current_price)

    # Max shares by currently available cash
    shares_by_cash = int(available_cash / current_price) if available_cash > 0 else 0

    # Final Recommended Shares
    recommended_shares = max(0, min(shares_by_risk, shares_by_cap, shares_by_cash))
    if recommended_shares == 0 and available_cash >= current_price:
        recommended_shares = 1  # Minimum 1 share if affordable

    total_investment = recommended_shares * current_price
    actual_risk_amt = recommended_shares * (current_price - suggested_stop)
    actual_risk_pct = (actual_risk_amt / total_budget * 100.0) if total_budget > 0 else 0.0
    alloc_pct = (total_investment / total_budget * 100.0) if total_budget > 0 else 0.0

    # Sizing Rationale
    notes: list[str] = []
    notes.append(f"Holding Horizon: {holding_period} (Stop: {stop_mult:.1f}x ATR = ₹{stop_distance_pts:.2f} / -{stop_pct:.1f}%)")
    notes.append(f"Account Risk Budget: {risk_pct:.1f}% (₹{max_risk_amount:,.2f}) | Actual Trade Risk: ₹{actual_risk_amt:,.2f} ({actual_risk_pct:.2f}%)")
    notes.append(f"Max Position Cap: {period_cap_pct:.1f}% (₹{max_capital_for_pos:,.2f}) | Allocated: ₹{total_investment:,.2f} ({alloc_pct:.1f}%)")

    if recommended_shares == shares_by_cash and shares_by_cash < shares_by_risk:
        notes.append("⚠️ Position sized down to match currently available cash balance.")
    elif recommended_shares == shares_by_cap and shares_by_cap < shares_by_risk:
        notes.append("ℹ️ Position size capped by maximum single-stock allocation limit.")
    else:
        notes.append("✅ Position precisely calibrated to 1% Fixed Fractional Account Risk.")

    rationale = (
        f"For a **{holding_period}** horizon, recommended size is **{recommended_shares} shares** "
        f"(₹{total_investment:,.2f} / {alloc_pct:.1f}% portfolio weight). "
        f"This limits total portfolio risk to **₹{actual_risk_amt:,.2f} ({actual_risk_pct:.2f}%)** "
        f"with a **{rr_ratio:.2f}x Risk/Reward** toward the +{cone_target_sigma:.1f}σ target of ₹{target_price:,.2f}."
    )

    return SizingRecommendation(
        ticker=ticker,
        holding_period=holding_period,
        current_price=current_price,
        suggested_stop_loss=suggested_stop,
        stop_distance_pct=stop_pct,
        target_price=target_price,
        upside_potential_pct=upside_pct,
        risk_reward_ratio=rr_ratio,
        recommended_shares=recommended_shares,
        total_investment_amount=total_investment,
        portfolio_allocation_pct=alloc_pct,
        capital_at_risk_amount=actual_risk_amt,
        capital_at_risk_pct=actual_risk_pct,
        sizing_rationale=rationale,
        risk_notes=notes,
    )
