from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from trading_bot.tema_macd.strategy import (
    tema_macd_fresh_bull_screen,
    tema_macd_fresh_bull_screen_tight,
)
from trading_bot.utility import (
    UNIVERSES,
    append_shared_report,
    config,
    fetch_data,
    get_fetch_data,
    shared_report_output_path,
)


def _ticker_cell(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "-"


def build_tema_macd_report(
    tight: bool = True,
    fetch_data_func=fetch_data,
    universes: list[tuple[str, list[str]]] | None = None,
) -> str:
    scanner = tema_macd_fresh_bull_screen_tight if tight else tema_macd_fresh_bull_screen
    as_of = datetime.now().isoformat(timespec="seconds")
    sections = [
        "## TEMA MACD",
        f"- Generated: `{as_of}`",
        f"- Tight mode: `{tight}`",
        "",
    ]

    target_universes = universes if universes is not None else UNIVERSES
    rows = []
    for segment, tickers in target_universes:
        daily = scanner(tickers, fetch_data_func, "D", config)
        weekly = scanner(tickers, fetch_data_func, "W", config)
        rows.append((segment, daily, weekly))

    sections.extend(
        [
            "### Summary",
            "| Segment | D Fresh Buy Count | W Fresh Buy Count |",
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
            "| Segment | D Fresh Buy | W Fresh Buy |",
            "|---|---|---|",
        ]
    )
    sections.extend(
        f"| {segment} | {_ticker_cell(daily)} | {_ticker_cell(weekly)} |"
        for segment, daily, weekly in rows
    )

    return "\n".join(sections)


def run_tema_macd_report(
    tight: bool = True,
    report_path: Path | None = None,
    *,
    refresh_data: bool = False,
    universes: list[tuple[str, list[str]]] | None = None,
) -> str:
    report = build_tema_macd_report(
        tight=tight,
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
    parser.add_argument("--tight", action="store_true")
    args = parser.parse_args()
    print(run_tema_macd_report(tight=args.tight, refresh_data=args.refresh_data))
