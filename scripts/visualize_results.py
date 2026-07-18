from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

RESULTS_PATH = Path("results/all_res.md")
OUTPUT_DIR = Path("results/visuals")


def parse_results_markdown(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    summary_rows: list[dict[str, object]] = []
    cone_rows: list[dict[str, object]] = []

    strategy = None
    subgroup = None
    current_universe = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if line.startswith("## Combination Strategy"):
            strategy = line.replace("## ", "").strip()
            subgroup = None
            current_universe = None
            i += 1
            continue

        if line.startswith("### ") and "Performance" in line:
            subgroup = line.replace("### ", "").strip()
            i += 1
            continue

        if line.startswith("#### ") and strategy == "Combination Strategy 1":
            current_universe = line.replace("#### ", "").strip()
            metrics = {}
            for j in range(i + 1, min(i + 8, len(lines))):
                metric_line = lines[j].strip()
                if metric_line.startswith("- Trade Count:"):
                    metrics["trade_count"] = float(_extract_number(metric_line))
                elif metric_line.startswith("- Avg Return per Trade:"):
                    metrics["avg_return_pct"] = float(_extract_number(metric_line))
                elif metric_line.startswith("- Win Rate:"):
                    metrics["win_rate_pct"] = float(_extract_number(metric_line))
                elif metric_line.startswith("- Median Trade Duration:"):
                    metrics["median_duration_days"] = float(_extract_number(metric_line))
            if metrics:
                summary_rows.append(
                    {
                        "strategy": subgroup,
                        "universe": current_universe,
                        **metrics,
                    }
                )
            i += 1
            continue

        if strategy in {
            "Combination Strategy 3",
            "Combination Strategy 5",
            "Combination Strategy 6",
        } and line.startswith("## N"):
            current_universe = line.replace("## ", "").strip()
            i += 1
            continue

        if line.startswith(
            "| Segment | Entry Cone Bucket | Trades | Avg Return % | Win Rate % | Median Duration (days) |"
        ):
            table_rows = []
            j = i + 2
            while j < len(lines):
                row_line = lines[j].strip()
                if not row_line.startswith("|"):
                    break
                parts = [part.strip() for part in row_line.strip("|").split("|")]
                if len(parts) == 6:
                    table_rows.append(parts)
                j += 1

            for parts in table_rows:
                segment, bucket, trades, avg_return, win_rate, median_duration = parts
                row = {
                    "strategy": strategy,
                    "universe": segment,
                    "bucket": bucket,
                    "trade_count": float(trades),
                    "avg_return_pct": float(avg_return),
                    "win_rate_pct": float(win_rate),
                    "median_duration_days": float(median_duration.replace("~", "")),
                }
                cone_rows.append(row)

            if strategy == "Combination Strategy 3":
                filtered = [
                    row
                    for row in cone_rows
                    if row["strategy"] == strategy and row["universe"] == current_universe
                ]
                if filtered:
                    total_trades = sum(row["trade_count"] for row in filtered)
                    summary_rows.append(
                        {
                            "strategy": "Combination Strategy 3",
                            "universe": current_universe,
                            "trade_count": total_trades,
                            "avg_return_pct": _weighted_average(filtered, "avg_return_pct"),
                            "win_rate_pct": _weighted_average(filtered, "win_rate_pct"),
                            "median_duration_days": _weighted_average(
                                filtered, "median_duration_days"
                            ),
                        }
                    )
            i = j
            continue

        i += 1

    summary_df = pd.DataFrame(summary_rows)
    cone_df = pd.DataFrame(cone_rows)
    return summary_df, cone_df


def _extract_number(line: str) -> float:
    match = re.search(r"([-+]?\d+(?:\.\d+)?)", line.replace(",", ""))
    if not match:
        raise ValueError(f"Could not parse number from: {line}")
    return float(match.group(1))


def _weighted_average(rows: list[dict[str, object]], value_key: str) -> float:
    total_weight = sum(float(row["trade_count"]) for row in rows)
    if total_weight == 0:
        return 0.0
    return sum(float(row[value_key]) * float(row["trade_count"]) for row in rows) / total_weight


def save_summary_files(summary_df: pd.DataFrame, cone_df: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(OUTPUT_DIR / "summary_metrics.csv", index=False)
    cone_df.to_csv(OUTPUT_DIR / "cone_bucket_metrics.csv", index=False)
    (OUTPUT_DIR / "summary_metrics.md").write_text(
        summary_df.to_markdown(index=False), encoding="utf-8"
    )


def plot_risk_return(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    size_scale = 0.05
    for _, row in summary_df.iterrows():
        ax.scatter(
            row["win_rate_pct"],
            row["avg_return_pct"],
            s=max(row["trade_count"] * size_scale, 40),
            alpha=0.7,
        )
        ax.annotate(
            f"{row['strategy'].replace('Combination Strategy ', 'S')}-{row['universe']}",
            (row["win_rate_pct"], row["avg_return_pct"]),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points",
        )
    ax.set_xlabel("Win Rate %")
    ax.set_ylabel("Average Return %")
    ax.set_title("Risk vs Return by Strategy and Universe")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "risk_return_scatter.png", dpi=200)
    plt.close(fig)


def plot_duration_vs_return(summary_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    size_scale = 0.05
    for _, row in summary_df.iterrows():
        ax.scatter(
            row["median_duration_days"],
            row["avg_return_pct"],
            s=max(row["trade_count"] * size_scale, 40),
            alpha=0.7,
        )
        ax.annotate(
            f"{row['strategy'].replace('Combination Strategy ', 'S')}-{row['universe']}",
            (row["median_duration_days"], row["avg_return_pct"]),
            fontsize=8,
            xytext=(4, 4),
            textcoords="offset points",
        )
    ax.set_xlabel("Median Duration (days)")
    ax.set_ylabel("Average Return %")
    ax.set_title("Return vs Holding Duration")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "duration_vs_return.png", dpi=200)
    plt.close(fig)


def plot_universe_heatmap(
    summary_df: pd.DataFrame, value_col: str, output_name: str, title: str
) -> None:
    pivot = summary_df.pivot(index="strategy", columns="universe", values=value_col).sort_index()
    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_title(title)
    for r in range(pivot.shape[0]):
        for c in range(pivot.shape[1]):
            value = pivot.iloc[r, c]
            ax.text(c, r, f"{value:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / output_name, dpi=200)
    plt.close(fig)


def plot_cone_heatmaps(cone_df: pd.DataFrame) -> None:
    cone_only = cone_df[
        cone_df["strategy"].isin(
            ["Combination Strategy 3", "Combination Strategy 5", "Combination Strategy 6"]
        )
    ].copy()
    strategies = cone_only["strategy"].drop_duplicates().tolist()

    fig, axes = plt.subplots(len(strategies), 2, figsize=(12, 4 * len(strategies)))
    if len(strategies) == 1:
        axes = [axes]

    for idx, strategy in enumerate(strategies):
        subset = cone_only[cone_only["strategy"] == strategy]
        for col_idx, (metric, title_suffix) in enumerate(
            [("avg_return_pct", "Avg Return %"), ("win_rate_pct", "Win Rate %")]
        ):
            pivot = subset.pivot(index="bucket", columns="universe", values=metric)
            ax = axes[idx][col_idx]
            im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels(pivot.columns)
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index)
            ax.set_title(f"{strategy} - {title_suffix}")
            for r in range(pivot.shape[0]):
                for c in range(pivot.shape[1]):
                    value = pivot.iloc[r, c]
                    ax.text(c, r, f"{value:.2f}", ha="center", va="center", fontsize=8)
            fig.colorbar(im, ax=ax, shrink=0.8)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "cone_bucket_heatmaps.png", dpi=200)
    plt.close(fig)


def main() -> None:
    if not RESULTS_PATH.exists():
        raise FileNotFoundError(f"Missing {RESULTS_PATH}")

    summary_df, cone_df = parse_results_markdown(RESULTS_PATH)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    save_summary_files(summary_df, cone_df)
    plot_risk_return(summary_df)
    plot_duration_vs_return(summary_df)
    plot_universe_heatmap(
        summary_df,
        "avg_return_pct",
        "universe_heatmap_return.png",
        "Universe Heatmap - Average Return %",
    )
    plot_universe_heatmap(
        summary_df, "win_rate_pct", "universe_heatmap_winrate.png", "Universe Heatmap - Win Rate %"
    )
    plot_cone_heatmaps(cone_df)
    print(f"Wrote visuals and summaries to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
