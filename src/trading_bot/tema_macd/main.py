from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from trading_bot.tema_macd.strategy import (
    tema_macd_fresh_bull_screen,
    tema_macd_fresh_bull_screen_tight,
)
from trading_bot.utility import (
    append_shared_report,
    config,
    fetch_data,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
    shared_report_output_path,
)


def _ticker_cell(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "-"


def build_tema_macd_report(tight: bool = True, fetch_data_func=fetch_data) -> str:
    scanner = tema_macd_fresh_bull_screen_tight if tight else tema_macd_fresh_bull_screen
    as_of = datetime.now().isoformat(timespec="seconds")
    sections = [
        "## TEMA MACD",
        f"- Generated: `{as_of}`",
        f"- Tight mode: `{tight}`",
        "",
    ]

    n50_d = scanner(nifty50_ns, fetch_data_func, "D", config)
    n150_d = scanner(nifty150_ns, fetch_data_func, "D", config)
    n250_d = scanner(nifty250_ns, fetch_data_func, "D", config)
    n50_w = scanner(nifty50_ns, fetch_data_func, "W", config)
    n150_w = scanner(nifty150_ns, fetch_data_func, "W", config)
    n250_w = scanner(nifty250_ns, fetch_data_func, "W", config)

    rows = [
        ("N50", n50_d, n50_w),
        ("N150", n150_d, n150_w),
        ("N250", n250_d, n250_w),
    ]

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
) -> str:
    report = build_tema_macd_report(
        tight=tight, fetch_data_func=get_fetch_data(refresh=refresh_data)
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
