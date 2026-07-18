from __future__ import annotations

from statistics import median

import numpy as np
import pandas as pd

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    _annual_volatility,
    _find_last_pivot,
    _resolve_bars_per_year,
)


def sigma_bucket(sigma_move: float) -> str:
    if sigma_move < -3.0:
        return "< -3sigma"
    if sigma_move < -2.0:
        return "-3sigma to -2sigma"
    if sigma_move < -1.0:
        return "-2sigma to -1sigma"
    if sigma_move < 0.0:
        return "-1sigma to 0sigma"
    if sigma_move < 1.0:
        return "0sigma to +1sigma"
    if sigma_move < 2.0:
        return "+1sigma to +2sigma"
    if sigma_move < 3.0:
        return "+2sigma to +3sigma"
    return "> +3sigma"


def entry_sigma_move(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    idx: int,
    freq: str,
    cone_config: ProjectionConeConfig,
) -> float | None:
    bars_per_year = _resolve_bars_per_year(freq, cone_config.bars_per_year)
    annual_vol = _annual_volatility(close[: idx + 1], cone_config.vol_length, bars_per_year)
    current_vol = float(annual_vol[-1])
    if np.isnan(current_vol) or current_vol <= 0:
        return None

    anchor_idx = idx
    anchor_price = float(close[idx])
    if cone_config.lock_mode:
        pivot_idx = _find_last_pivot(
            high[: idx + 1],
            low[: idx + 1],
            cone_config.pivot_len,
            cone_config.lock_to_bull,
        )
        if pivot_idx is not None and not np.isnan(annual_vol[pivot_idx]):
            anchor_idx = pivot_idx
            anchor_price = float(low[pivot_idx] if cone_config.lock_to_bull else high[pivot_idx])

    t_now = max(idx - anchor_idx, 1)
    return float(
        np.log(float(close[idx]) / anchor_price)
        / (current_vol * np.sqrt(float(t_now) / float(bars_per_year)))
    )


def metrics_from_trades(trades: list[dict[str, float]], label: str) -> dict[str, float]:
    if not trades:
        raise ValueError(f"No trades generated for {label}")

    returns = [trade["return_pct"] for trade in trades]
    durations = [trade["duration_days"] for trade in trades]
    wins = [value for value in returns if value > 0]
    return {
        "trade_count": float(len(trades)),
        "avg_return_pct": float(sum(returns) / len(returns)),
        "win_rate_pct": float(len(wins) / len(returns) * 100.0),
        "median_duration_days": float(median(durations)),
    }


def append_trade(
    trades: list[dict[str, float]],
    *,
    entry_price: float,
    exit_price: float,
    entry_time,
    exit_time,
    sigma_move: float,
    sigma_bucket_value: str,
) -> None:
    duration = pd.Timestamp(exit_time) - pd.Timestamp(entry_time)
    trades.append(
        {
            "return_pct": (exit_price / entry_price - 1.0) * 100.0,
            "duration_days": float(duration / pd.Timedelta(days=1)),
            "sigma_move": sigma_move,
            "sigma_bucket": sigma_bucket_value,
        }
    )
