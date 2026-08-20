from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

OUTPUT_DIR = Path("results/experiments")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def plot_noise_vs_quality() -> None:
    strategies = [
        "Baseline TEMA-MACD MTF",
        "Baseline Supertrend MTF",
        "ST MTF + Sigma <= 0.0 + 200 SMA",
        "ST MTF + Sigma <= 0.0 + 200 SMA + ADX (Top Sharpe)",
        "Elite Quantum ST (Top Profit Factor)",
    ]
    trades = [11554, 1046, 603, 341, 152]
    profit_factors = [2.11, 4.13, 4.28, 4.47, 5.77]
    avg_returns = [3.31, 16.94, 17.43, 19.19, 28.59]
    win_rates = [41.56, 48.66, 46.77, 49.56, 46.71]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Trade Noise / Churn Reduction
    ax = axes[0, 0]
    bars = ax.bar(range(len(strategies)), trades, color=["#e57373", "#ffb74d", "#64b5f6", "#81c784", "#4db6ac"])
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(["TEMA-MACD", "ST Benchmark", "ST+SMA200", "ST+SMA+ADX", "Elite Quantum"], rotation=15, fontsize=9)
    ax.set_title("Trade Count (Noise Reduction)", fontsize=11, fontweight="bold")
    ax.set_yscale("log")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() * 1.1, f"{int(bar.get_height())}", ha="center", fontsize=8)

    # 2. Profit Factor
    ax = axes[0, 1]
    bars = ax.bar(range(len(strategies)), profit_factors, color=["#e57373", "#ffb74d", "#64b5f6", "#81c784", "#2e7d32"])
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(["TEMA-MACD", "ST Benchmark", "ST+SMA200", "ST+SMA+ADX", "Elite Quantum"], rotation=15, fontsize=9)
    ax.set_title("Profit Factor (Gross Profit / Gross Loss)", fontsize=11, fontweight="bold")
    ax.axhline(4.0, color="gray", linestyle="--", alpha=0.5)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f"{bar.get_height():.2f}", ha="center", fontsize=8)

    # 3. Average Return per Trade %
    ax = axes[1, 0]
    bars = ax.bar(range(len(strategies)), avg_returns, color=["#e57373", "#ffb74d", "#64b5f6", "#81c784", "#1b5e20"])
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(["TEMA-MACD", "ST Benchmark", "ST+SMA200", "ST+SMA+ADX", "Elite Quantum"], rotation=15, fontsize=9)
    ax.set_title("Average Return per Trade (%)", fontsize=11, fontweight="bold")
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.1f}%", ha="center", fontsize=8)

    # 4. Win Rate %
    ax = axes[1, 1]
    bars = ax.bar(range(len(strategies)), win_rates, color=["#e57373", "#ffb74d", "#64b5f6", "#81c784", "#4db6ac"])
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(["TEMA-MACD", "ST Benchmark", "ST+SMA200", "ST+SMA+ADX", "Elite Quantum"], rotation=15, fontsize=9)
    ax.set_title("Win Rate (%)", fontsize=11, fontweight="bold")
    ax.set_ylim(30, 55)
    ax.axhline(50, color="gray", linestyle="--", alpha=0.5)
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, f"{bar.get_height():.1f}%", ha="center", fontsize=8)

    fig.tight_layout()
    chart_path = OUTPUT_DIR / "strategy_noise_and_quality_breakdown.png"
    fig.savefig(chart_path, dpi=200)
    plt.close(fig)
    print(f"Saved chart to {chart_path}")


def main() -> None:
    plot_noise_vs_quality()


if __name__ == "__main__":
    main()
