from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from research.experiments.advanced_strategies import (
    run_mtf_pullback_ema_rebound,
    run_mtf_squeeze_expansion,
    run_weekly_donchian_turtle,
    run_weekly_supertrend_cone_value,
    run_weekly_supertrend_momentum,
    run_weekly_tema_macd_cone_value,
)
from research.experiments.engine import PerformanceMetrics, Trade, compute_trade_metrics
from research.experiments.strategies import (
    run_baseline_supertrend_mtf,
    run_baseline_tema_macd_mtf,
    run_strategy_adaptive_hull_trend,
    run_strategy_triple_confluence_quantum,
)
from trading_bot.utility import (
    MarketDataStore,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)

STRATEGY_REGISTRY = {
    "1. Baseline TEMA-MACD MTF": run_baseline_tema_macd_mtf,
    "2. Baseline Supertrend MTF": run_baseline_supertrend_mtf,
    "3. Weekly Supertrend Multi-Scale Momentum": run_weekly_supertrend_momentum,
    "4. Weekly TEMA-MACD + Cone Value (C5+)": run_weekly_tema_macd_cone_value,
    "5. Weekly Supertrend + Cone Value (C6+)": run_weekly_supertrend_cone_value,
    "6. MTF Squeeze Expansion (Weekly Trend + Daily Squeeze)": run_mtf_squeeze_expansion,
    "7. Dual-Momentum Pullback EMA Rebound": run_mtf_pullback_ema_rebound,
    "8. Weekly Donchian Turtle 2.0": run_weekly_donchian_turtle,
    "9. Adaptive Hull Trend Engine": run_strategy_adaptive_hull_trend,
    "10. Triple Confluence Quantum Model": run_strategy_triple_confluence_quantum,
}

UNIVERSE_MAP = {
    "N150": nifty150_ns,
    "N250": nifty250_ns,
    "N50": nifty50_ns,
}


def run_single_ticker_strategy(
    strategy_func: Any,
    ticker: str,
    fetch_data_func: Any,
) -> list[Trade]:
    try:
        daily_df = fetch_data_func(ticker, type="D")
        weekly_df = fetch_data_func(ticker, type="W")
        return strategy_func(daily_df, weekly_df, ticker)
    except Exception:
        return []


def run_experiment_on_universe(
    universe_name: str,
    tickers: list[str],
    fetch_data_func: Any,
    max_workers: int = 8,
) -> dict[str, tuple[PerformanceMetrics, list[Trade]]]:
    results: dict[str, tuple[PerformanceMetrics, list[Trade]]] = {}

    print("\n=======================================================")
    print(f"Running Experiment on Universe: {universe_name} ({len(tickers)} tickers)")
    print("=======================================================")

    for strat_name, strat_func in STRATEGY_REGISTRY.items():
        t0 = time.time()
        all_trades: list[Trade] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(run_single_ticker_strategy, strat_func, ticker, fetch_data_func): ticker
                for ticker in tickers
            }
            for future in as_completed(futures):
                trades = future.result()
                all_trades.extend(trades)

        metrics = compute_trade_metrics(all_trades, strategy_name=strat_name, universe=universe_name)
        elapsed = time.time() - t0
        print(
            f"-> [{strat_name}] Trades: {metrics.trade_count} | WR: {metrics.win_rate_pct}% | "
            f"PF: {metrics.profit_factor} | AvgRet: {metrics.avg_return_pct}% | "
            f"MaxDD: {metrics.max_drawdown_pct}% | Sharpe: {metrics.sharpe_ratio} ({elapsed:.1f}s)"
        )
        results[strat_name] = (metrics, all_trades)

    return results


def generate_experiment_report(
    universe_results: dict[str, dict[str, tuple[PerformanceMetrics, list[Trade]]]],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_file = output_dir / "research_experiment_report.md"

    lines = [
        "# Quantitative Strategy Research & Benchmark Report",
        f"- Generated: `{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        "- Universe: **Nifty Midcap 150 (`N150`)** (Primary) with Out-of-Sample Validation",
        "- Objective: Maximize Win Rate, Profit Factor, Risk-Adjusted Returns while minimizing drawdowns & noise.",
        "",
        "---",
        "",
    ]

    for universe_name, strat_data in universe_results.items():
        lines.extend(
            [
                f"## Universe: {universe_name}",
                "",
                "| Strategy | Trades | Win Rate % | Profit Factor | Avg Return % | Median Return % | Expectancy % | Sharpe | Sortino | Max DD % | Median Days | Max Loss % |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )

        # Sort by Composite Performance Score
        ranked = []
        for _strat_name, (metrics, _) in strat_data.items():
            score = (
                (metrics.win_rate_pct / 50.0)
                * metrics.profit_factor
                * max(0.1, metrics.sharpe_ratio)
                / max(5.0, metrics.max_drawdown_pct / 2.0)
            )
            ranked.append((score, metrics))

        ranked.sort(key=lambda x: x[0], reverse=True)

        for _, m in ranked:
            lines.append(
                f"| **{m.strategy_name}** | {m.trade_count} | **{m.win_rate_pct}%** | "
                f"**{m.profit_factor}** | {m.avg_return_pct}% | {m.median_return_pct}% | "
                f"**{m.expectancy_pct}%** | **{m.sharpe_ratio}** | {m.sortino_ratio} | "
                f"**{m.max_drawdown_pct}%** | {m.median_duration_days} | {m.max_loss_pct}% |"
            )

        lines.append("")

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return report_file


def plot_experiment_charts(
    universe_results: dict[str, dict[str, tuple[PerformanceMetrics, list[Trade]]]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for universe_name, strat_data in universe_results.items():
        strategies = list(strat_data.keys())
        win_rates = [strat_data[s][0].win_rate_pct for s in strategies]
        profit_factors = [strat_data[s][0].profit_factor for s in strategies]
        sharpes = [strat_data[s][0].sharpe_ratio for s in strategies]
        max_dds = [strat_data[s][0].max_drawdown_pct for s in strategies]
        short_names = [s.split(". ")[-1] for s in strategies]

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        y_pos = np.arange(len(short_names))

        # Win Rate
        ax = axes[0, 0]
        bars = ax.barh(y_pos, win_rates, color="#2b5c8f", alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(short_names, fontsize=9)
        ax.axvline(50, color="gray", linestyle="--", alpha=0.6)
        ax.set_title(f"Win Rate % - {universe_name}", fontsize=11, fontweight="bold")
        for bar in bars:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, f"{bar.get_width():.1f}%", va="center", fontsize=8)

        # Profit Factor
        ax = axes[0, 1]
        bars = ax.barh(y_pos, profit_factors, color="#2e7d32", alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([])
        ax.axvline(1.5, color="gray", linestyle="--", alpha=0.6)
        ax.set_title(f"Profit Factor - {universe_name}", fontsize=11, fontweight="bold")
        for bar in bars:
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height()/2, f"{bar.get_width():.2f}", va="center", fontsize=8)

        # Sharpe Ratio
        ax = axes[1, 0]
        bars = ax.barh(y_pos, sharpes, color="#6a1b9a", alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(short_names, fontsize=9)
        ax.axvline(1.0, color="gray", linestyle="--", alpha=0.6)
        ax.set_title(f"Sharpe Ratio - {universe_name}", fontsize=11, fontweight="bold")
        for bar in bars:
            ax.text(max(0, bar.get_width()) + 0.05, bar.get_y() + bar.get_height()/2, f"{bar.get_width():.2f}", va="center", fontsize=8)

        # Max Drawdown % (Lower is better)
        ax = axes[1, 1]
        bars = ax.barh(y_pos, max_dds, color="#c62828", alpha=0.85)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([])
        ax.set_title(f"Max Drawdown % (Lower Better) - {universe_name}", fontsize=11, fontweight="bold")
        for bar in bars:
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, f"{bar.get_width():.1f}%", va="center", fontsize=8)

        fig.tight_layout()
        fig.savefig(output_dir / f"strategy_comparison_{universe_name}.png", dpi=200)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="N150", choices=["N150", "N250", "N50", "all"])
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    store = MarketDataStore()
    fetcher = get_fetch_data(refresh=args.refresh_data, store=store)

    target_universes = ["N150"] if args.universe == "N150" else (["N150", "N250", "N50"] if args.universe == "all" else [args.universe])

    universe_results: dict[str, dict[str, tuple[PerformanceMetrics, list[Trade]]]] = {}

    for univ in target_universes:
        tickers = UNIVERSE_MAP[univ]
        results = run_experiment_on_universe(univ, tickers, fetcher, max_workers=args.max_workers)
        universe_results[univ] = results

    output_dir = Path("results/experiments")
    report_file = generate_experiment_report(universe_results, output_dir)
    plot_experiment_charts(universe_results, output_dir)

    print("\n=======================================================")
    print(f"Research Experiment Complete! Report saved to {report_file}")
    print(f"Charts saved to {output_dir}/")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
