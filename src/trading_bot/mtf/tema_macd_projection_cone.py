from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    _annual_volatility,
    _find_last_pivot,
    _resolve_bars_per_year,
)
from trading_bot.tema_macd.strategy import _latest_complete_bar_index, _tema_macd_state
from trading_bot.utility import (
    config,
    ensure_output_dir,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


@dataclass(frozen=True)
class TemaMacdProjectionConeMatch:
    ticker: str
    segment: str
    daily_bar_time: str
    weekly_bar_time: str
    current_price: float
    sigma_move: float
    sigma_bucket: str
    anchor_price: float
    anchor_type: str
    weekly_state: str = "bull"
    daily_signal: str = "fresh_buy"


def _sigma_bucket(sigma_move: float) -> str:
    if sigma_move < -3.0:
        return "< -3σ"
    if sigma_move < -2.0:
        return "-3σ to -2σ"
    if sigma_move < -1.0:
        return "-2σ to -1σ"
    if sigma_move < 0.0:
        return "-1σ to 0σ"
    if sigma_move < 1.0:
        return "0σ to +1σ"
    if sigma_move < 2.0:
        return "+1σ to +2σ"
    if sigma_move < 3.0:
        return "+2σ to +3σ"
    return "> +3σ"


def _daily_sigma_snapshot(
    data: pd.DataFrame,
    idx: int,
    cone_config: ProjectionConeConfig,
) -> dict[str, Any] | None:
    close = np.asarray(data["close"].values, dtype=float).ravel()
    high = np.asarray(data["high"].values, dtype=float).ravel()
    low = np.asarray(data["low"].values, dtype=float).ravel()

    bars_per_year = _resolve_bars_per_year("D", cone_config.bars_per_year)
    annual_vol = _annual_volatility(close[: idx + 1], cone_config.vol_length, bars_per_year)
    current_vol = float(annual_vol[-1])
    if np.isnan(current_vol) or current_vol <= 0:
        return None

    anchor_idx = idx
    anchor_type = "live_close"
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
            anchor_type = "pivot_low" if cone_config.lock_to_bull else "pivot_high"
            anchor_price = float(low[pivot_idx] if cone_config.lock_to_bull else high[pivot_idx])

    t_now = max(idx - anchor_idx, 1)
    sigma_move = float(
        np.log(float(close[idx]) / anchor_price)
        / (current_vol * np.sqrt(float(t_now) / float(bars_per_year)))
    )

    return {
        "sigma_move": sigma_move,
        "sigma_bucket": _sigma_bucket(sigma_move),
        "anchor_price": anchor_price,
        "anchor_type": anchor_type,
    }


def scan_tema_macd_projection_cone(
    tickers: list[str],
    fetch_data_func,
    *,
    segment: str,
    tema_config: dict[str, int],
    cone_config: ProjectionConeConfig | None = None,
    min_negative_sigma: float = -1.0,
) -> list[TemaMacdProjectionConeMatch]:
    cone_config = cone_config or ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    matches: list[TemaMacdProjectionConeMatch] = []

    for ticker in tickers:
        try:
            daily_data = fetch_data_func(ticker, type="D")
            weekly_data = fetch_data_func(ticker, type="W")

            daily_close = np.asarray(daily_data["close"].values, dtype=float).ravel()
            daily_time_values = np.asarray(daily_data["time"].values)
            weekly_close = np.asarray(weekly_data["close"].values, dtype=float).ravel()
            weekly_time_values = np.asarray(weekly_data["time"].values)

            if len(daily_close) < max(tema_config["tema_len"], tema_config["macd_slow"]) + 5:
                continue
            if len(weekly_close) < max(tema_config["tema_len"], tema_config["macd_slow"]) + 5:
                continue

            daily_idx = _latest_complete_bar_index(daily_time_values, "D")
            weekly_idx = _latest_complete_bar_index(weekly_time_values, "W")
            if daily_idx is None or daily_idx <= 0 or weekly_idx is None or weekly_idx <= 0:
                continue

            daily_tema, daily_macd, daily_signal, daily_state_before, _ = _tema_macd_state(
                daily_close, tema_config
            )
            _, _, _, _, weekly_state_after = _tema_macd_state(weekly_close, tema_config)

            if (
                np.isnan(daily_tema[daily_idx])
                or np.isnan(daily_macd[daily_idx])
                or np.isnan(daily_signal[daily_idx])
            ):
                continue

            daily_fresh_buy = (
                daily_tema[daily_idx] >= daily_tema[daily_idx - 1]
                and not daily_state_before[daily_idx]
                and daily_macd[daily_idx] >= daily_signal[daily_idx]
            )
            weekly_bull = bool(weekly_state_after[weekly_idx])

            if not daily_fresh_buy or not weekly_bull:
                continue

            cone_snapshot = _daily_sigma_snapshot(daily_data, daily_idx, cone_config)
            if cone_snapshot is None or cone_snapshot["sigma_move"] >= min_negative_sigma:
                continue

            matches.append(
                TemaMacdProjectionConeMatch(
                    ticker=ticker,
                    segment=segment,
                    daily_bar_time=str(pd.to_datetime(daily_data["time"].iloc[daily_idx])),
                    weekly_bar_time=str(pd.to_datetime(weekly_data["time"].iloc[weekly_idx])),
                    current_price=float(daily_close[daily_idx]),
                    sigma_move=float(cone_snapshot["sigma_move"]),
                    sigma_bucket=str(cone_snapshot["sigma_bucket"]),
                    anchor_price=float(cone_snapshot["anchor_price"]),
                    anchor_type=str(cone_snapshot["anchor_type"]),
                )
            )
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")

    return matches


def build_markdown_report(
    matches: list[TemaMacdProjectionConeMatch], *, min_negative_sigma: float
) -> str:
    ordered_matches = sorted(matches, key=lambda match: (float(match.sigma_move), match.ticker))
    sections = [
        "## TEMA MACD D in W + Projection Cone D",
        "",
        "- Rule:",
        "- `D` fresh buy",
        "- `W` already bull",
        f"- `D` cone sigma deviation `< {min_negative_sigma}`",
        "",
        "| Segment | Ticker | Daily Bar | Weekly Bar | Price | Sigma Move | Sigma Bucket | Anchor Type | Anchor Price |",
        "|---|---|---|---|---:|---:|---|---|---:|",
    ]

    for match in ordered_matches:
        sections.append(
            f"| {match.segment} | `{match.ticker}` | {match.daily_bar_time} | {match.weekly_bar_time} | "
            f"{match.current_price:.2f} | {match.sigma_move:.2f} | {match.sigma_bucket} | "
            f"{match.anchor_type} | {match.anchor_price:.2f} |"
        )

    if not matches:
        sections.append("| - | - | - | - | - | - | - | - | - |")

    sections.extend(
        [
            "",
            "### Count By Segment",
            "",
            "| Segment | Matches |",
            "|---|---:|",
        ]
    )
    counts: dict[str, int] = {"N50": 0, "N150": 0, "N250": 0}
    for match in ordered_matches:
        counts[match.segment] += 1
    sections.extend(f"| {segment} | {count} |" for segment, count in counts.items())

    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--min-negative-sigma", type=float, default=-1.0)
    args = parser.parse_args()

    fetch_data_func = get_fetch_data(refresh=args.refresh_data)
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)

    matches: list[TemaMacdProjectionConeMatch] = []
    matches.extend(
        scan_tema_macd_projection_cone(
            nifty50_ns,
            fetch_data_func,
            segment="N50",
            tema_config=config,
            cone_config=cone_config,
            min_negative_sigma=args.min_negative_sigma,
        )
    )
    matches.extend(
        scan_tema_macd_projection_cone(
            nifty150_ns,
            fetch_data_func,
            segment="N150",
            tema_config=config,
            cone_config=cone_config,
            min_negative_sigma=args.min_negative_sigma,
        )
    )
    matches.extend(
        scan_tema_macd_projection_cone(
            nifty250_ns,
            fetch_data_func,
            segment="N250",
            tema_config=config,
            cone_config=cone_config,
            min_negative_sigma=args.min_negative_sigma,
        )
    )

    report = build_markdown_report(matches, min_negative_sigma=args.min_negative_sigma)
    output_dir = ensure_output_dir("results")
    output_path = output_dir / "tema_macd_projection_cone_mtf_latest.md"
    output_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nSaved report to {output_path}")


if __name__ == "__main__":
    main()
