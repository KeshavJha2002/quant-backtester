from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.utility.indicators import rma, true_range


@dataclass
class StructuralPatternAnalysis:
    ticker: str
    vcp_compression_ratio: float  # < 0.8 is strong compression (ready to explode)
    accumulation_volume_ratio: float  # > 1.2 indicates institutional accumulation
    rs_momentum_pct: float  # Relative strength / 20-day return %
    distance_to_52w_high_pct: float  # < 10% is near breakout / blue sky
    cone_risk_reward_ratio: float  # Potential gain to +2.0σ vs downside to -1.0σ
    structural_score: float  # 0 to 100
    key_strengths: list[str]
    key_risks: list[str]
    verdict: str


def analyze_structural_patterns(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
    sigma_move: float = 0.0,
) -> StructuralPatternAnalysis:
    close = np.asarray(daily_df["close"].values, float).ravel()
    high = np.asarray(daily_df["high"].values, float).ravel()
    low = np.asarray(daily_df["low"].values, float).ravel()
    vol = np.asarray(daily_df["volume"].values, float).ravel()
    n = len(close)

    if n < 40:
        return StructuralPatternAnalysis(
            ticker=ticker,
            vcp_compression_ratio=1.0,
            accumulation_volume_ratio=1.0,
            rs_momentum_pct=0.0,
            distance_to_52w_high_pct=50.0,
            cone_risk_reward_ratio=1.0,
            structural_score=50.0,
            key_strengths=["Insufficient data history for deep structural pattern scan"],
            key_risks=["Low history"],
            verdict="Neutral",
        )

    # 1. Volatility Contraction Pattern (VCP)
    tr = true_range(high, low, close)
    atr5 = float(rma(tr, 5)[-1])
    atr20 = float(rma(tr, 20)[-1])
    vcp_ratio = (atr5 / atr20) if atr20 > 0 else 1.0

    # 2. Accumulation vs Distribution Volume
    # Up-day volume vs down-day volume over last 20 days
    up_days = close[-20:] > np.roll(close[-20:], 1)
    up_days[0] = False
    up_vol = np.sum(vol[-20:][up_days])
    down_vol = np.sum(vol[-20:][~up_days])
    acc_ratio = (up_vol / down_vol) if down_vol > 0 else 1.0

    # 3. 20-Day Momentum / Relative Strength
    ret_20d = ((close[-1] - close[-20]) / close[-20]) * 100.0 if n >= 20 else 0.0

    # 4. Distance to 52-Week High
    high_52w = float(pd.Series(high).rolling(min(252, n), min_periods=20).max().iloc[-1])
    dist_52w_high = max(0.0, ((high_52w - close[-1]) / high_52w) * 100.0)

    # 5. Projection Cone Risk/Reward Asymmetry
    # Upside to +2.0σ vs Downside to -1.0σ (where current sigma is sigma_move)
    upside_sigmas = max(0.2, 2.0 - sigma_move)
    downside_sigmas = max(0.4, sigma_move - (-1.0))
    cone_rr = upside_sigmas / downside_sigmas

    # Compute Structural Quality Score (0 to 100)
    score = 50.0
    strengths: list[str] = []
    risks: list[str] = []

    # Score adjustments based on quantitative structural rules:
    if vcp_ratio <= 0.75:
        score += 15.0
        strengths.append(f"Strong Volatility Contraction (VCP Ratio: {vcp_ratio:.2f}) → Energy coiled for explosive breakout")
    elif vcp_ratio >= 1.25:
        score -= 10.0
        risks.append(f"High Volatility Expansion (ATR5/ATR20: {vcp_ratio:.2f}) → Choppy/whipsaw conditions")

    if acc_ratio >= 1.30:
        score += 15.0
        strengths.append(f"Institutional Accumulation (Up/Down Vol: {acc_ratio:.2f}x) → Smart money buying on volume")
    elif acc_ratio <= 0.70:
        score -= 12.0
        risks.append(f"Distribution Warning (Up/Down Vol: {acc_ratio:.2f}x) → Selling pressure on high volume")

    if dist_52w_high <= 8.0:
        score += 12.0
        strengths.append(f"Near 52-Week High ({dist_52w_high:.1f}% away) → Blue-sky breakout with minimal overhead resistance")
    elif dist_52w_high >= 30.0:
        score -= 10.0
        risks.append(f"Deep in 52-Week Range ({dist_52w_high:.1f}% below high) → Potential overhead supply resistance")

    if sigma_move <= 0.0:
        score += 10.0
        strengths.append(f"Discount Valuation (Sigma: {sigma_move:+.2f}σ) → Favorable asymmetric entry inside trend")
    elif sigma_move >= 1.8:
        score -= 15.0
        risks.append(f"Extended Valuation (Sigma: {sigma_move:+.2f}σ) → High mean-reversion pullback risk")

    score = float(np.clip(score, 5.0, 98.0))

    if score >= 75:
        verdict = "High Conviction Institutional Setup (Prime Candidate)"
    elif score >= 55:
        verdict = "Moderate Quality Setup (Standard Position)"
    else:
        verdict = "Sub-Optimal Structure (Higher Noise / Distribution Risk)"

    return StructuralPatternAnalysis(
        ticker=ticker,
        vcp_compression_ratio=float(vcp_ratio),
        accumulation_volume_ratio=float(acc_ratio),
        rs_momentum_pct=float(ret_20d),
        distance_to_52w_high_pct=float(dist_52w_high),
        cone_risk_reward_ratio=float(cone_rr),
        structural_score=score,
        key_strengths=strengths,
        key_risks=risks,
        verdict=verdict,
    )


def compare_two_stocks_tie_breaker(
    analysis_a: StructuralPatternAnalysis,
    analysis_b: StructuralPatternAnalysis,
) -> dict[str, Any]:
    """Deterministic structural tie-breaker between two candidate stocks."""
    score_diff = analysis_a.structural_score - analysis_b.structural_score

    if score_diff >= 5.0:
        winner = analysis_a.ticker
        rationale = (
            f"**{analysis_a.ticker}** is statistically superior (+{score_diff:.1f} pts higher structural score). "
            f"Key edge: Accumulation volume ({analysis_a.accumulation_volume_ratio:.2f}x vs {analysis_b.accumulation_volume_ratio:.2f}x) "
            f"and VCP compression ({analysis_a.vcp_compression_ratio:.2f} vs {analysis_b.vcp_compression_ratio:.2f})."
        )
    elif score_diff <= -5.0:
        winner = analysis_b.ticker
        rationale = (
            f"**{analysis_b.ticker}** is statistically superior (+{abs(score_diff):.1f} pts higher structural score). "
            f"Key edge: Accumulation volume ({analysis_b.accumulation_volume_ratio:.2f}x vs {analysis_a.accumulation_volume_ratio:.2f}x) "
            f"and VCP compression ({analysis_b.vcp_compression_ratio:.2f} vs {analysis_a.vcp_compression_ratio:.2f})."
        )
    else:
        # Close score: break tie by distance to 52w high and cone risk/reward
        if analysis_a.distance_to_52w_high_pct < analysis_b.distance_to_52w_high_pct:
            winner = analysis_a.ticker
            rationale = (
                f"**{analysis_a.ticker}** wins the close tie-breaker due to proximity to 52-week high "
                f"({analysis_a.distance_to_52w_high_pct:.1f}% vs {analysis_b.distance_to_52w_high_pct:.1f}% away), "
                f"offering clearer blue-sky breakout upside with less overhead resistance."
            )
        else:
            winner = analysis_b.ticker
            rationale = (
                f"**{analysis_b.ticker}** wins the close tie-breaker due to proximity to 52-week high "
                f"({analysis_b.distance_to_52w_high_pct:.1f}% vs {analysis_a.distance_to_52w_high_pct:.1f}% away), "
                f"offering clearer blue-sky breakout upside with less overhead resistance."
            )

    return {
        "winner": winner,
        "rationale": rationale,
        "stock_a": analysis_a,
        "stock_b": analysis_b,
    }
