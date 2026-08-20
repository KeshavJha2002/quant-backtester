from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Trade:
    ticker: str
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    return_pct: float
    duration_days: float
    exit_reason: str
    mfe_pct: float = 0.0  # Max Favorable Excursion
    mae_pct: float = 0.0  # Max Adverse Excursion
    entry_sigma: float | None = None
    timeframe: str = "D"


@dataclass(frozen=True)
class PerformanceMetrics:
    strategy_name: str
    universe: str
    trade_count: int
    win_rate_pct: float
    profit_factor: float
    avg_return_pct: float
    median_return_pct: float
    win_loss_ratio: float
    expectancy_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    median_duration_days: float
    calmar_ratio: float
    max_win_pct: float
    max_loss_pct: float
    total_pnl_pct: float


def compute_trade_metrics(
    trades: list[Trade],
    strategy_name: str = "Strategy",
    universe: str = "N150",
    risk_free_rate: float = 0.06,
) -> PerformanceMetrics:
    """Compute institutional performance metrics from a list of trade records."""
    valid_trades = [
        t
        for t in trades
        if not np.isnan(t.return_pct)
        and not np.isinf(t.return_pct)
        and not np.isnan(t.duration_days)
    ]

    if not valid_trades:
        return PerformanceMetrics(
            strategy_name=strategy_name,
            universe=universe,
            trade_count=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            avg_return_pct=0.0,
            median_return_pct=0.0,
            win_loss_ratio=0.0,
            expectancy_pct=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown_pct=0.0,
            median_duration_days=0.0,
            calmar_ratio=0.0,
            max_win_pct=0.0,
            max_loss_pct=0.0,
            total_pnl_pct=0.0,
        )

    returns = np.array([t.return_pct for t in valid_trades], dtype=float)
    durations = np.array([t.duration_days for t in valid_trades], dtype=float)

    wins = returns[returns > 0]
    losses = returns[returns <= 0]

    trade_count = len(returns)
    win_count = len(wins)
    win_rate_pct = (win_count / trade_count) * 100.0 if trade_count > 0 else 0.0

    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
    gross_loss = float(np.abs(np.sum(losses))) if len(losses) > 0 else 1e-8
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 99.0

    avg_win = float(np.mean(wins)) if len(wins) > 0 else 0.0
    avg_loss = float(np.abs(np.mean(losses))) if len(losses) > 0 else 1e-8
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0

    avg_return_pct = float(np.mean(returns)) if len(returns) > 0 else 0.0
    median_return_pct = float(np.median(returns)) if len(returns) > 0 else 0.0
    median_duration = float(np.median(durations)) if len(durations) > 0 else 0.0

    # Expectancy (% per trade) = (Win% * AvgWin) - (Loss% * AvgLoss)
    win_prob = win_rate_pct / 100.0
    loss_prob = 1.0 - win_prob
    expectancy_pct = (win_prob * avg_win) - (loss_prob * avg_loss)

    # Cumulative equity curve & Max Drawdown
    equity_curve = np.cumprod(np.maximum(0.01, 1.0 + returns / 100.0))
    running_max = np.maximum.accumulate(equity_curve)
    drawdowns = (equity_curve - running_max) / running_max * 100.0
    max_drawdown_pct = float(np.abs(np.min(drawdowns))) if len(drawdowns) > 0 else 0.0

    # Sharpe and Sortino Ratios (per-trade basis annualized proxy)
    ret_std = float(np.std(returns)) if len(returns) > 1 else 1e-8
    downside_returns = returns[returns < 0]
    downside_std = float(np.std(downside_returns)) if len(downside_returns) > 1 else 1e-8

    # Approximate annualization factor based on median holding duration
    trades_per_year = 252.0 / max(1.0, median_duration)
    rf_per_trade = (risk_free_rate / max(1.0, trades_per_year)) * 100.0

    excess_returns = returns - rf_per_trade
    sharpe_ratio = (
        float(np.mean(excess_returns) / ret_std * np.sqrt(trades_per_year))
        if ret_std > 1e-6
        else 0.0
    )
    sortino_ratio = (
        float(np.mean(excess_returns) / downside_std * np.sqrt(trades_per_year))
        if downside_std > 1e-6
        else 0.0
    )

    total_pnl_pct = (equity_curve[-1] - 1.0) * 100.0 if len(equity_curve) > 0 else 0.0
    calmar_ratio = (
        (avg_return_pct * trades_per_year) / max_drawdown_pct
        if max_drawdown_pct > 1e-4
        else 0.0
    )

    return PerformanceMetrics(
        strategy_name=strategy_name,
        universe=universe,
        trade_count=trade_count,
        win_rate_pct=round(win_rate_pct, 2),
        profit_factor=round(profit_factor, 2),
        avg_return_pct=round(avg_return_pct, 2),
        median_return_pct=round(median_return_pct, 2),
        win_loss_ratio=round(win_loss_ratio, 2),
        expectancy_pct=round(expectancy_pct, 2),
        sharpe_ratio=round(sharpe_ratio, 2),
        sortino_ratio=round(sortino_ratio, 2),
        max_drawdown_pct=round(max_drawdown_pct, 2),
        median_duration_days=round(median_duration, 1),
        calmar_ratio=round(calmar_ratio, 2),
        max_win_pct=round(float(np.max(returns)), 2) if len(returns) > 0 else 0.0,
        max_loss_pct=round(float(np.min(returns)), 2) if len(returns) > 0 else 0.0,
        total_pnl_pct=round(total_pnl_pct, 2),
    )


def simulate_trades(
    daily_df: pd.DataFrame,
    entry_signals: np.ndarray,
    exit_signals: np.ndarray,
    ticker: str = "TICKER",
    atr_trailing_mult: float | None = None,
    hard_stop_pct: float | None = None,
    profit_target_pct: float | None = None,
    time_stop_bars: int | None = None,
    slippage_pct: float = 0.15,  # 0.15% roundtrip cost
    entry_sigma_values: np.ndarray | None = None,
    timeframe: str = "D",
) -> list[Trade]:
    """Simulate trade execution from boolean entry/exit signals with dynamic risk management."""
    close = np.asarray(daily_df["close"].values, dtype=float).ravel()
    high = np.asarray(daily_df["high"].values, dtype=float).ravel()
    low = np.asarray(daily_df["low"].values, dtype=float).ravel()
    time_series = pd.to_datetime(daily_df["time"].values)

    n = len(close)
    if n < 5:
        return []

    # Calculate ATR for dynamic trailing stop if requested
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for k in range(1, n):
        tr[k] = max(high[k] - low[k], abs(high[k] - close[k - 1]), abs(low[k] - close[k - 1]))
    atr_series = pd.Series(tr).rolling(14, min_periods=1).mean().to_numpy()

    trades: list[Trade] = []
    in_position = False
    entry_idx = 0
    entry_price = 0.0
    highest_price_since_entry = 0.0
    lowest_price_since_entry = 0.0
    current_stop = 0.0
    target_price = 0.0
    entry_sigma = None

    for i in range(1, n):
        if not in_position:
            if entry_signals[i] and not np.isnan(close[i]) and close[i] > 0:
                in_position = True
                entry_idx = i
                entry_price = close[i] * (1.0 + (slippage_pct / 200.0))
                highest_price_since_entry = high[i]
                lowest_price_since_entry = low[i]
                entry_sigma = (
                    float(entry_sigma_values[i])
                    if entry_sigma_values is not None and not np.isnan(entry_sigma_values[i])
                    else None
                )

                # Initialize stops
                current_stop = 0.0
                if hard_stop_pct is not None:
                    current_stop = entry_price * (1.0 - (hard_stop_pct / 100.0))
                if atr_trailing_mult is not None and not np.isnan(atr_series[i]):
                    atr_stop = entry_price - (atr_trailing_mult * atr_series[i])
                    current_stop = max(current_stop, atr_stop)

                target_price = (
                    entry_price * (1.0 + (profit_target_pct / 100.0))
                    if profit_target_pct is not None
                    else float("inf")
                )
            continue

        # While in position, track MFE and MAE
        if not np.isnan(high[i]):
            highest_price_since_entry = max(highest_price_since_entry, high[i])
        if not np.isnan(low[i]):
            lowest_price_since_entry = min(lowest_price_since_entry, low[i])

        # Update ATR trailing stop
        if atr_trailing_mult is not None and not np.isnan(atr_series[i]):
            trailing_stop = highest_price_since_entry - (atr_trailing_mult * atr_series[i])
            current_stop = max(current_stop, trailing_stop)

        # Check Exit Conditions:
        exit_triggered = False
        exit_price = close[i]
        exit_reason = "Signal Exit"

        # 1. Hard Stop / Trailing Stop Hit (check if low breached stop)
        if current_stop > 0 and not np.isnan(low[i]) and low[i] <= current_stop:
            exit_triggered = True
            exit_price = min(close[i], current_stop)
            exit_reason = "Trailing Stop / Stop Loss"

        # 2. Profit Target Hit
        elif profit_target_pct is not None and not np.isnan(high[i]) and high[i] >= target_price:
            exit_triggered = True
            exit_price = max(close[i], target_price)
            exit_reason = "Profit Target"

        # 3. Strategy Signal Exit
        elif exit_signals[i]:
            exit_triggered = True
            exit_price = close[i]
            exit_reason = "Signal Exit"

        # 4. Time-based Stagnation Exit
        elif time_stop_bars is not None and (i - entry_idx) >= time_stop_bars:
            exit_triggered = True
            exit_price = close[i]
            exit_reason = "Time Stagnation Exit"

        # If exited or end of series reached
        if exit_triggered or i == n - 1:
            in_position = False
            if np.isnan(exit_price) or exit_price <= 0 or np.isnan(entry_price) or entry_price <= 0:
                continue

            exit_price_net = exit_price * (1.0 - (slippage_pct / 200.0))
            return_pct = (exit_price_net / entry_price - 1.0) * 100.0
            duration_days = float(
                (pd.to_datetime(time_series[i]) - pd.to_datetime(time_series[entry_idx])).total_seconds()
                / 86400.0
            )

            mfe_pct = (highest_price_since_entry / entry_price - 1.0) * 100.0
            mae_pct = (lowest_price_since_entry / entry_price - 1.0) * 100.0

            trades.append(
                Trade(
                    ticker=ticker,
                    entry_time=str(time_series[entry_idx].date()),
                    exit_time=str(time_series[i].date()),
                    entry_price=entry_price,
                    exit_price=exit_price_net,
                    return_pct=return_pct,
                    duration_days=duration_days,
                    exit_reason=exit_reason,
                    mfe_pct=mfe_pct,
                    mae_pct=mae_pct,
                    entry_sigma=entry_sigma,
                    timeframe=timeframe,
                )
            )

    return trades
