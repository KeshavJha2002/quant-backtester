from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import pandas as pd

from research.experiments.advanced_quant_strategies import (
    run_connors_rsi2_cone_hybrid,
    run_connors_rsi2_mean_reversion,
    run_donovanwall_range_filter,
    run_double_7s_mean_reversion,
    run_kaufman_adaptive_trend,
    run_minervini_vcp_breakout,
    run_nadaraya_watson_envelope_bounce,
    run_ultra_high_wr_stage2_connors_hybrid,
)
from research.experiments.engine import PerformanceMetrics, Trade, compute_trade_metrics
from research.experiments.optimize_supertrend_cone import (
    StrategyVariant,
    run_supertrend_cone_variant,
)
from trading_bot.utility import (
    MarketDataStore,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


@dataclass
class QuantStrategyConfig:
    name: str
    runner: Callable[[pd.DataFrame, pd.DataFrame, str], list[Trade]]
    category: str


def run_c7_quantum_wrapper(d_df: pd.DataFrame, w_df: pd.DataFrame, ticker: str) -> list[Trade]:
    variant = StrategyVariant(
        name="C7 Elite Quantum Supertrend MTF + Cone Discount",
        max_sigma=0.0,
        require_sma200=True,
        require_volume=True,
        require_adx=True,
        exit_mode="st_grace_2",
    )
    return run_supertrend_cone_variant(d_df, w_df, ticker, variant)


def plot_quant_comparison(metrics: list[PerformanceMetrics], output_dir: Path) -> None:
    names = [m.strategy_name.split(":")[0].replace("Strategy ", "") for m in metrics]
    win_rates = [m.win_rate_pct for m in metrics]
    profit_factors = [m.profit_factor for m in metrics]
    sharpes = [m.sharpe_ratio for m in metrics]
    trades = [m.trade_count for m in metrics]

    fig, axes = plt.subplots(2, 2, figsize=(15, 11))

    # 1. Win Rate %
    ax = axes[0, 0]
    bars = ax.bar(range(len(metrics)), win_rates, color="#388e3c")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax.set_title("Win Rate (%) across N150", fontsize=11, fontweight="bold")
    ax.axhline(50, color="gray", linestyle="--", alpha=0.5)
    ax.axhline(60, color="green", linestyle=":", alpha=0.5)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.1f}%", ha="center", fontsize=8)

    # 2. Profit Factor
    ax = axes[0, 1]
    bars = ax.bar(range(len(metrics)), profit_factors, color="#1976d2")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax.set_title("Profit Factor", fontsize=11, fontweight="bold")
    ax.axhline(2.0, color="gray", linestyle="--", alpha=0.5)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05, f"{bar.get_height():.2f}", ha="center", fontsize=8)

    # 3. Sharpe Ratio
    ax = axes[1, 0]
    bars = ax.bar(range(len(metrics)), sharpes, color="#7b1fa2")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax.set_title("Sharpe Ratio (Annualized)", fontsize=11, fontweight="bold")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, f"{bar.get_height():.2f}", ha="center", fontsize=8)

    # 4. Trade Count (Noise Profile)
    ax = axes[1, 1]
    bars = ax.bar(range(len(metrics)), trades, color="#f57c00")
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(names, rotation=35, ha="right", fontsize=8)
    ax.set_title("Trade Count (Noise vs Selectivity)", fontsize=11, fontweight="bold")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"{int(bar.get_height())}", ha="center", fontsize=8)

    fig.tight_layout()
    chart_path = output_dir / "advanced_quant_comparison.png"
    fig.savefig(chart_path, dpi=200)
    plt.close(fig)
    print(f"Comparison chart saved to {chart_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="N150", choices=["N150", "N250", "N50", "all"])
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()

    store = MarketDataStore()
    fetcher = get_fetch_data(refresh=False, store=store)

    strategies: list[QuantStrategyConfig] = [
        QuantStrategyConfig("Q0: Benchmark C7 Quantum ST MTF", run_c7_quantum_wrapper, "Multi-Timeframe Trend"),
        QuantStrategyConfig("Q1: Connors RSI(2) Mean Reversion (> 200 SMA)", run_connors_rsi2_mean_reversion, "Mean Reversion"),
        QuantStrategyConfig("Q2: Connors RSI(2) + Cone Deep Value Hybrid", run_connors_rsi2_cone_hybrid, "Hybrid Mean-Reversion"),
        QuantStrategyConfig("Q3: Double 7s Mean Reversion in Bull Trend", run_double_7s_mean_reversion, "Mean Reversion"),
        QuantStrategyConfig("Q4: Minervini Stage 2 + VCP Breakout", run_minervini_vcp_breakout, "Momentum Breakout"),
        QuantStrategyConfig("Q5: Kaufman Adaptive Trend (KAMA + ER > 0.32)", run_kaufman_adaptive_trend, "Adaptive Trend"),
        QuantStrategyConfig("Q6: DonovanWall Range Filter Momentum", run_donovanwall_range_filter, "Trend Following"),
        QuantStrategyConfig("Q7: Nadaraya-Watson Non-Repainting Kernel Bounce", run_nadaraya_watson_envelope_bounce, "Non-Parametric Kernel"),
        QuantStrategyConfig("Q8: Minervini Stage 2 + Connors RSI(2) Confluence", run_ultra_high_wr_stage2_connors_hybrid, "Hybrid Confluence"),
    ]

    target_universes = ["N150"] if args.universe == "N150" else (["N150", "N250", "N50"] if args.universe == "all" else [args.universe])
    output_dir = Path("results/experiments")
    output_dir.mkdir(parents=True, exist_ok=True)

    for univ in target_universes:
        tickers = nifty150_ns if univ == "N150" else (nifty250_ns if univ == "N250" else nifty50_ns)
        print("\n=======================================================")
        print(f"Running Advanced Quant Research Benchmark on {univ} ({len(tickers)} tickers)")
        print("=======================================================")

        metrics_list: list[PerformanceMetrics] = []

        for strat in strategies:
            t0 = time.time()
            all_trades: list[Trade] = []

            def _worker(ticker: str, runner: Callable = strat.runner) -> list[Trade]:
                try:
                    d_df = fetcher(ticker, type="D")
                    w_df = fetcher(ticker, type="W")
                    return runner(d_df, w_df, ticker)
                except Exception:
                    return []

            with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
                futures = {executor.submit(_worker, ticker): ticker for ticker in tickers}
                for f in as_completed(futures):
                    all_trades.extend(f.result())

            m = compute_trade_metrics(all_trades, strategy_name=strat.name, universe=univ)
            metrics_list.append(m)
            elapsed = time.time() - t0
            print(
                f"-> [{strat.name}] Trades: {m.trade_count} | WR: {m.win_rate_pct}% | PF: {m.profit_factor} | "
                f"AvgRet: {m.avg_return_pct}% | MedDur: {m.median_duration_days}d | Sharpe: {m.sharpe_ratio} ({elapsed:.1f}s)"
            )

        # Plot charts
        plot_quant_comparison(metrics_list, output_dir)

        # Generate Detailed Markdown Report
        report_path = output_dir / f"advanced_quant_research_report_{univ}.md"
        lines = [
            f"# Advanced Quantitative Research & Paper Benchmark Report ({univ})",
            f"- Generated: `{pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}`",
            f"- Universe: **{univ}** ({len(tickers)} liquid tickers)",
            "- Scope: State-of-the-Art Quant Literature, TradingView Pioneers, Larry Connors Mean Reversion, Mark Minervini Trend Templates, Kaufman Adaptive KAMA, DonovanWall Range Filters, Nadaraya-Watson Non-Parametric Kernel Envelopes, and Hybrid Cone Confluences.",
            "",
            "---",
            "",
            "| Strategy Archetype | Category | Trades | Win Rate % | Profit Factor | Avg Return % | Median Return % | Expectancy % | Sharpe | Sortino | Max DD % | Median Days |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for m, strat in zip(metrics_list, strategies, strict=False):
            lines.append(
                f"| **{m.strategy_name}** | {strat.category} | {m.trade_count} | **{m.win_rate_pct}%** | **{m.profit_factor}** | "
                f"{m.avg_return_pct}% | {m.median_return_pct}% | **{m.expectancy_pct}%** | **{m.sharpe_ratio}** | "
                f"{m.sortino_ratio} | **{m.max_drawdown_pct}%** | {m.median_duration_days} |"
            )
        lines.append("")

        report_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
