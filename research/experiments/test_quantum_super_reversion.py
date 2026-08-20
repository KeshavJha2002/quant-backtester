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

from research.experiments.advanced_quant_indicators import compute_rsi_2
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
class SuperReversionVariant:
    name: str
    rsi2_threshold: float
    max_sigma: float
    require_st_pullback: bool
    exit_type: str  # "st_slow_flip", "st_grace_2", "cone_target_2sigma", "cone_target_2_5sigma"


def run_super_reversion_trade_sim(
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    ticker: str,
    variant: SuperReversionVariant,
) -> list[Trade]:
    daily_close = np.asarray(daily_df["close"].values, float).ravel()
    daily_high = np.asarray(daily_df["high"].values, float).ravel()
    daily_low = np.asarray(daily_df["low"].values, float).ravel()
    daily_vol = np.asarray(daily_df["volume"].values, float).ravel()

    weekly_close = np.asarray(weekly_df["close"].values, float).ravel()
    weekly_high = np.asarray(weekly_df["high"].values, float).ravel()
    weekly_low = np.asarray(weekly_df["low"].values, float).ravel()

    if len(daily_close) < 210 or len(weekly_close) < 25:
        return []

    # Weekly Macro Regime: Triple Supertrend
    w_t1, w_t2, w_t3 = compute_triple_supertrend(weekly_close, weekly_high, weekly_low)
    w_bull = (w_t1 == 1) | (w_t2 == 1) | (w_t3 == 1)
    w_bull_on_d = align_weekly_to_daily(daily_df["time"], weekly_df["time"], w_bull)

    # Daily Indicators
    d_fast = compute_st_trend_from_config(daily_close, daily_high, daily_low, 10, 3.0, 1)
    d_slow = compute_st_trend_from_config(daily_close, daily_high, daily_low, 14, 3.5, 3)
    d_sma200 = sma(daily_close, 200)
    d_vol_sma = sma(daily_vol, 20)
    _, _, d_adx = compute_adx(daily_high, daily_low, daily_close, 14)
    rsi2 = compute_rsi_2(daily_close)

    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    sigma_vals = compute_series_entry_sigmas(daily_close, daily_high, daily_low, "D", cone_config)

    n = len(daily_close)
    entries = np.zeros(n, dtype=bool)
    exits = np.zeros(n, dtype=bool)

    fast_bear_count = 0

    for i in range(200, n):
        sigma = sigma_vals[i]

        # 1. Macro Regime Filter: Weekly Bull + Price >= 200 SMA * 0.98
        macro_ok = bool(w_bull_on_d[i] and (np.isnan(d_sma200[i]) or daily_close[i] >= d_sma200[i] * 0.98))

        # 2. Trigger Conditions:
        # A) Larry Connors oversold panic dip (RSI2 <= threshold) inside weekly bull
        rsi_dip = bool(not np.isnan(rsi2[i]) and rsi2[i] <= variant.rsi2_threshold)

        # B) Daily Supertrend Pullback Flip
        st_pullback = bool(d_fast[i - 1] == -1 and d_fast[i] == 1 and d_slow[i] == 1)

        trigger_ok = (rsi_dip or st_pullback) if not variant.require_st_pullback else (rsi_dip and st_pullback)

        # 3. Valuation & Momentum Filters
        cone_ok = bool(sigma is not None and not np.isnan(sigma) and sigma <= variant.max_sigma)
        vol_ok = bool(np.isnan(d_vol_sma[i]) or daily_vol[i] >= 0.8 * d_vol_sma[i])
        adx_ok = bool(np.isnan(d_adx[i]) or d_adx[i] >= 16.0)

        if macro_ok and trigger_ok and cone_ok and vol_ok and adx_ok:
            entries[i] = True

        # 4. Trend-Riding Exits:
        if variant.exit_type == "st_slow_flip":
            if d_slow[i] == -1:
                exits[i] = True
        elif variant.exit_type == "st_grace_2":
            if d_slow[i] == -1:
                exits[i] = True
                fast_bear_count = 0
            elif d_fast[i] == -1:
                fast_bear_count += 1
                if fast_bear_count >= 2:
                    exits[i] = True
            else:
                fast_bear_count = 0
        elif variant.exit_type == "cone_target_2sigma":
            if d_slow[i] == -1 or (sigma is not None and not np.isnan(sigma) and sigma >= 2.0):
                exits[i] = True
        elif variant.exit_type == "cone_target_2_5sigma":
            if d_slow[i] == -1 or (sigma is not None and not np.isnan(sigma) and sigma >= 2.5):
                exits[i] = True

    return simulate_trades(
        daily_df,
        entries,
        exits,
        ticker=ticker,
        hard_stop_pct=6.5,
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

    variants: list[SuperReversionVariant] = [
        SuperReversionVariant("1. Hybrid: Connors RSI2(<=10) + Cone(<=0.0) + ST Slow Exit", 10.0, 0.0, False, "st_slow_flip"),
        SuperReversionVariant("2. Hybrid: Connors RSI2(<=10) + Cone(<=0.0) + ST Grace 2 Exit", 10.0, 0.0, False, "st_grace_2"),
        SuperReversionVariant("3. Hybrid: Connors RSI2(<=10) + Cone(<=0.0) + Cone +2.0σ Exit", 10.0, 0.0, False, "cone_target_2sigma"),
        SuperReversionVariant("4. Hybrid: Connors RSI2(<=10) + Cone(<=0.0) + Cone +2.5σ Exit", 10.0, 0.0, False, "cone_target_2_5sigma"),
        SuperReversionVariant("5. Hybrid: Connors RSI2(<=15) + Cone(<=-0.2) + ST Grace 2 Exit", 15.0, -0.2, False, "st_grace_2"),
        SuperReversionVariant("6. Hybrid: Connors RSI2(<=15) + Cone(<=-0.2) + Cone +2.0σ Exit", 15.0, -0.2, False, "cone_target_2sigma"),
        SuperReversionVariant("7. Confluence: RSI2(<=15) AND ST Pullback + Cone(<=0.0) + ST Grace 2", 15.0, 0.0, True, "st_grace_2"),
        SuperReversionVariant("8. Confluence: RSI2(<=15) AND ST Pullback + Cone(<=-0.2) + Cone +2.0σ", 15.0, -0.2, True, "cone_target_2sigma"),
        SuperReversionVariant("9. Elite Deep Value: RSI2(<=8) + Cone(<=-0.5) + ST Grace 2", 8.0, -0.5, False, "st_grace_2"),
        SuperReversionVariant("10. Elite Deep Value: RSI2(<=8) + Cone(<=-0.5) + Cone +2.0σ Target", 8.0, -0.5, False, "cone_target_2sigma"),
    ]

    target_universes = ["N150"] if args.universe == "N150" else (["N150", "N250", "N50"] if args.universe == "all" else [args.universe])

    for univ in target_universes:
        tickers = nifty150_ns if univ == "N150" else (nifty250_ns if univ == "N250" else nifty50_ns)
        print("\n=======================================================")
        print(f"Testing Quantum Super-Reversion Hybrids on {univ} ({len(tickers)} tickers)")
        print("=======================================================")

        metrics_list: list[PerformanceMetrics] = []

        for var in variants:
            t0 = time.time()
            all_trades: list[Trade] = []

            def _worker(ticker: str, v: SuperReversionVariant = var) -> list[Trade]:
                try:
                    d_df = fetcher(ticker, type="D")
                    w_df = fetcher(ticker, type="W")
                    return run_super_reversion_trade_sim(d_df, w_df, ticker, v)
                except Exception:
                    return []

            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                futures = {executor.submit(_worker, ticker): ticker for ticker in tickers}
                for f in as_completed(futures):
                    all_trades.extend(f.result())

            m = compute_trade_metrics(all_trades, strategy_name=var.name, universe=univ)
            metrics_list.append(m)
            elapsed = time.time() - t0
            print(
                f"[{var.name}] Trades: {m.trade_count} | WR: {m.win_rate_pct}% | PF: {m.profit_factor} | "
                f"AvgRet: {m.avg_return_pct}% | MedDur: {m.median_duration_days}d | Sharpe: {m.sharpe_ratio} ({elapsed:.1f}s)"
            )

        # Output report
        output_dir = Path("results/experiments")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / f"quantum_super_reversion_report_{univ}.md"
        lines = [
            f"# Quantum Super-Reversion Research Report ({univ})",
            f"- Generated: `{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}`",
            "- Concept: Combining Larry Connors RSI(2) Extreme Panic Dips with Multi-Timeframe Supertrend Trend-Riding and Projection Cone Valuation",
            "",
            "---",
            "",
            "| Strategy Hybrid | Trades | Win Rate % | Profit Factor | Avg Return % | Median Return % | Expectancy % | Sharpe | Sortino | Max DD % | Median Days |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for m in metrics_list:
            lines.append(
                f"| **{m.strategy_name}** | {m.trade_count} | **{m.win_rate_pct}%** | **{m.profit_factor}** | "
                f"{m.avg_return_pct}% | {m.median_return_pct}% | **{m.expectancy_pct}%** | **{m.sharpe_ratio}** | "
                f"{m.sortino_ratio} | **{m.max_drawdown_pct}%** | {m.median_duration_days} |"
            )
        lines.append("")
        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Saved report to {report_path}")


if __name__ == "__main__":
    main()
