from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from trading_bot.supertrend.strategy import run_supertrend_scans
from trading_bot.utility import (
    UNIVERSES,
    append_shared_report,
    fetch_data,
    get_fetch_data,
    shared_report_output_path,
)


def _ticker_cell(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "-"


def build_supertrend_report(
    fetch_data_func=fetch_data,
    universes: list[tuple[str, list[str]]] | None = None,
) -> str:
    as_of = datetime.now().isoformat(timespec="seconds")
    sections = ["## Supertrend", f"- Generated: `{as_of}`", ""]

    target_universes = universes if universes is not None else UNIVERSES
    rows = []
    for segment, tickers in target_universes:
        _, recent_d, _ = run_supertrend_scans(tickers, fetch_data_func, "D", mode="pullback")
        _, _, recent_w = run_supertrend_scans(tickers, fetch_data_func, "W", mode="or")
        rows.append((segment, recent_d["D"], recent_w["W"]))

    sections.extend(
        [
            "### Summary",
            "| Segment | D Pullback Count | W Fresh Count |",
            "|---|---:|---:|",
        ]
    )
    sections.extend(
        f"| {segment} | {len(daily)} | {len(weekly)} |" for segment, daily, weekly in rows
    )
    sections.append("")
    sections.extend(
        [
            "### Tickers",
            "| Segment | D Pullback | W Fresh |",
            "|---|---|---|",
        ]
    )
    sections.extend(
        f"| {segment} | {_ticker_cell(daily)} | {_ticker_cell(weekly)} |"
        for segment, daily, weekly in rows
    )

    return "\n".join(sections)


def run_supertrend_report(
    report_path: Path | None = None,
    *,
    refresh_data: bool = False,
    universes: list[tuple[str, list[str]]] | None = None,
) -> str:
    report = build_supertrend_report(
        fetch_data_func=get_fetch_data(refresh=refresh_data),
        universes=universes,
    )
    if report_path is None:
        report_path = shared_report_output_path(datetime.now().strftime("%Y-%m-%d"))
    append_shared_report(report_path, report)
    return str(report_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()
    print(run_supertrend_report(refresh_data=args.refresh_data))
