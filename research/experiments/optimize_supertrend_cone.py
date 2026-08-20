from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from research.experiments.engine import (
    PerformanceMetrics,
    Trade,
    compute_trade_metrics,
    simulate_trades,
)
from research.experiments.indicators import compute_adx
from research.experiments.strategies import align_weekly_to_daily
from trading_bot.projection_cone import ProjectionConeConfig, compute_series_entry_sigmas
from trading_bot.utility import (
    MarketDataStore,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)
from trading_bot.utility.indicators import (
    compute_st_trend_from_config,
    compute_triple_supertrend,
    sma,
)


@dataclass
class StrategyVariant:
    name: str
    max_sigma: float
    require_sma200: bool
    require_volume: bool
    require_adx: bool
    exit_mode: str  # "st_flip", "st_grace_2", "cone_target", "atr_trail"


def run_supertrend_cone_variant(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
    variant: StrategyVariant,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()
    daily_vol = np.asarray(daily_df["volume"].values, float).ravel()

    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(daily_close) < 40 or len(weekly_close) < 25:
        return []

    # Indicators
    d_fast = compute_st_trend_from_config(daily_close, daily_high, daily_low, 10, 3.0, 1)
    d_slow = compute_st_trend_from_config(daily_close, daily_high, daily_low, 14, 3.5, 3)

    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    d_sma200 = sma(daily_close, min(200, len(daily_close) // 2))
    d_vol_sma = sma(daily_vol, 20)
    _, _, d_adx = compute_adx(daily_high, daily_low, daily_close, 14)

    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(daily_close, daily_high, daily_low, "D", cone_config)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    fast_bear_count = 0

    for i in range(2, n):
        sigma = sigma_vals[i]

        # Base Trigger: Daily ST fast flips to bull while Slow ST is bull & Weekly is bull
        base_trigger = bool(
            d_fast[i - 1] == -1
            and d_fast[i] == 1
            and d_slow[i] == 1
            and w_bull_on_d[i]
        )

        # Filters
        sigma_ok = bool(sigma is not None and not np.isnan(sigma) and sigma <= variant.max_sigma)
        sma_ok = bool(not variant.require_sma200 or (np.isnan(d_sma200[i]) or daily_close[i] >= d_sma200[i] * 0.98))
        vol_ok = bool(not variant.require_volume or (np.isnan(d_vol_sma[i]) or daily_vol[i] >= 1.0 * d_vol_sma[i]))
        adx_ok = bool(not variant.require_adx or (np.isnan(d_adx[i]) or d_adx[i] >= 18.0))

        if base_trigger and sigma_ok and sma_ok and vol_ok and adx_ok:
            entries[i] = True

        # Exits
        if variant.exit_mode == "st_flip":
            if d_slow[i] == -1 or d_fast[i] == -1:
                exits[i] = True
        elif variant.exit_mode == "st_grace_2":
            if d_slow[i] == -1:
                exits[i] = True
                fast_bear_count = 0
            elif d_fast[i] == -1:
                fast_bear_count += 1
                if fast_bear_count >= 2:
                    exits[i] = True
            else:
                fast_bear_count = 0
        elif variant.exit_mode == "cone_target":
            # Exit if supertrend breaks OR if price reached upper cone +2.0 sigma
            if d_slow[i] == -1 or (sigma is not None and not np.isnan(sigma) and sigma >= 2.0):
                exits[i] = True
        elif variant.exit_mode == "atr_trail":
            if d_slow[i] == -1:
                exits[i] = True

    atr_mult = 3.0 if variant.exit_mode == "atr_trail" else None
    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        atr_trailing_mult=atr_mult,
        entry_sigma_values=sigma_vals,
        slippage_pct=0.15,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="N150", choices=["N150", "N250", "N50", "all"])
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    store = MarketDataStore()
    fetcher = get_fetch_data(refresh=False, store=store)

    variants: list[StrategyVariant] = [
        StrategyVariant("1. Benchmark ST MTF (No Sigma Filter)", 99.0, False, False, False, "st_grace_2"),
        StrategyVariant("2. ST MTF + Sigma <= 0.5 (Neutral/Discount)", 0.5, False, False, False, "st_grace_2"),
        StrategyVariant("3. ST MTF + Sigma <= 0.0 (Only Discount)", 0.0, False, False, False, "st_grace_2"),
        StrategyVariant("4. ST MTF + Sigma <= -0.5 (Deep Value)", -0.5, False, False, False, "st_grace_2"),
        StrategyVariant("5. ST MTF + Sigma <= 0.0 + 200 SMA", 0.0, True, False, False, "st_grace_2"),
        StrategyVariant("6. ST MTF + Sigma <= 0.0 + 200 SMA + Volume", 0.0, True, True, False, "st_grace_2"),
        StrategyVariant("7. ST MTF + Sigma <= 0.0 + 200 SMA + ADX", 0.0, True, False, True, "st_grace_2"),
        StrategyVariant("8. ST MTF + Sigma <= 0.0 + Cone +2σ Target", 0.0, True, True, False, "cone_target"),
        StrategyVariant("9. ST MTF + Sigma <= 0.0 + 3.0x ATR Trail", 0.0, True, False, False, "atr_trail"),
        StrategyVariant("10. Elite Quantum ST (Sigma <= -0.2 + 200 SMA + Vol + Cone Target)", -0.2, True, True, True, "cone_target"),
    ]

    target_universes = ["N150"] if args.universe == "N150" else (["N150", "N250", "N50"] if args.universe == "all" else [args.universe])
    all_universe_results: dict[str, list[PerformanceMetrics]] = {}

    for univ in target_universes:
        tickers = nifty150_ns if univ == "N150" else (nifty250_ns if univ == "N250" else nifty50_ns)
        print("\n=======================================================")
        print(f"Optimizing Supertrend-Cone Variants on {univ} ({len(tickers)} tickers)")
        print("=======================================================")

        metrics_list: list[PerformanceMetrics] = []

        for var in variants:
            t0 = time.time()
            all_trades: list[Trade] = []

            def _run(ticker: str, v: StrategyVariant = var) -> list[Trade]:
                try:
                    d_df = fetcher(ticker, type="D")
                    w_df = fetcher(ticker, type="W")
                    return run_supertrend_cone_variant(d_df, w_df, ticker, v)
                except Exception:
                    return []

            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                futures = {executor.submit(_run, ticker): ticker for ticker in tickers}
                for f in as_completed(futures):
                    all_trades.extend(f.result())

            m = compute_trade_metrics(all_trades, strategy_name=var.name, universe=univ)
            metrics_list.append(m)
            elapsed = time.time() - t0
            print(
                f"[{var.name}] Trades: {m.trade_count} | WR: {m.win_rate_pct}% | PF: {m.profit_factor} | "
                f"AvgRet: {m.avg_return_pct}% | MaxDD: {m.max_drawdown_pct}% | Sharpe: {m.sharpe_ratio} ({elapsed:.1f}s)"
            )

        all_universe_results[univ] = metrics_list

    # Generate Markdown Report
    output_dir = Path("results/experiments")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "supertrend_cone_optimization_report.md"

    lines = [
        "# Supertrend + Projection Cone Optimization Report",
        f"- Generated: `{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "- Depth Analysis across Sigma Thresholds, Regime Filters, and Dynamic Cone Exits",
        "",
        "---",
        "",
    ]

    for univ, metrics_list in all_universe_results.items():
        lines.extend(
            [
                f"## Universe: {univ}",
                "",
                "| Strategy Variant | Trades | Win Rate % | Profit Factor | Avg Return % | Median Return % | Expectancy % | Sharpe | Sortino | Max DD % | Median Days | Max Loss % |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for m in metrics_list:
            lines.append(
                f"| **{m.strategy_name}** | {m.trade_count} | **{m.win_rate_pct}%** | **{m.profit_factor}** | "
                f"{m.avg_return_pct}% | {m.median_return_pct}% | **{m.expectancy_pct}%** | **{m.sharpe_ratio}** | "
                f"{m.sortino_ratio} | **{m.max_drawdown_pct}%** | {m.median_duration_days} | {m.max_loss_pct}% |"
            )
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nOptimization complete! Report saved to {report_path}")


if __name__ == "__main__":
    main()
