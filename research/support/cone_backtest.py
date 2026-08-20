from __future__ import annotations

from statistics import median
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    calculate_entry_sigma,
    get_sigma_bucket,
)


def sigma_bucket(sigma_move: float) -> str:
    """Categorize sigma move into ASCII-formatted bucket string for research suite compatibility."""
    return get_sigma_bucket(sigma_move, unicode_symbol=False)


def entry_sigma_move(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    idx: int,
    freq: str,
    cone_config: ProjectionConeConfig,
) -> float | None:
    """Calculate entry sigma move for a bar at index idx."""
    return calculate_entry_sigma(close, high, low, idx, freq, cone_config)


def metrics_from_trades(trades: list[dict[str, Any]], label: str) -> dict[str, float]:
    """Compute aggregate performance metrics from a list of simulated trade dicts."""
    if not trades:
        raise ValueError(f"No trades generated for {label}")

    returns = [float(trade["return_pct"]) for trade in trades]
    durations = [float(trade["duration_days"]) for trade in trades]
    wins = [value for value in returns if value > 0]
    return {
        "trade_count": float(len(trades)),
        "avg_return_pct": float(sum(returns) / len(returns)),
        "win_rate_pct": float(len(wins) / len(returns) * 100.0),
        "median_duration_days": float(median(durations)),
    }


def append_trade(
    trades: list[dict[str, Any]],
    *,
    entry_price: float,
    exit_price: float,
    entry_time: Any,
    exit_time: Any,
    sigma_move: float,
    sigma_bucket_value: str,
) -> None:
    """Calculate trade return & duration and append trade record to trades list."""
    duration_seconds = (pd.to_datetime(exit_time) - pd.to_datetime(entry_time)).total_seconds()
    trades.append(
        {
            "return_pct": (exit_price / entry_price - 1.0) * 100.0,
            "duration_days": float(duration_seconds / 86400.0),
            "sigma_move": sigma_move,
            "sigma_bucket": sigma_bucket_value,
        }
    )
