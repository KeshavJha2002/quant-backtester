from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from trading_bot.mtf.supertrend import run_supertrend_mtf_scan
from trading_bot.mtf.tema_macd import run_tema_macd_mtf_scan
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


def build_mtf_report(tight: bool = False, fetch_data_func=fetch_data) -> str:
    as_of = datetime.now().isoformat(timespec="seconds")
    sections = [
        "## MTF",
        f"- Generated: `{as_of}`",
        f"- Tight mode: `{tight}`",
        "",
        "### Summary",
        "| Strategy | Segment | D within W Count |",
        "|---|---|---:|",
    ]

    super_n50_d, _ = run_supertrend_mtf_scan(nifty50_ns, fetch_data_func)
    super_n150_d, _ = run_supertrend_mtf_scan(nifty150_ns, fetch_data_func)
    super_n250_d, _ = run_supertrend_mtf_scan(nifty250_ns, fetch_data_func)
    tema_n50_d, _ = run_tema_macd_mtf_scan(nifty50_ns, fetch_data_func, config, tight=tight)
    tema_n150_d, _ = run_tema_macd_mtf_scan(nifty150_ns, fetch_data_func, config, tight=tight)
    tema_n250_d, _ = run_tema_macd_mtf_scan(nifty250_ns, fetch_data_func, config, tight=tight)

    supertrend_rows = [
        ("Supertrend", "N50", super_n50_d),
        ("Supertrend", "N150", super_n150_d),
        ("Supertrend", "N250", super_n250_d),
    ]
    tema_rows = [
        ("TEMA MACD", "N50", tema_n50_d),
        ("TEMA MACD", "N150", tema_n150_d),
        ("TEMA MACD", "N250", tema_n250_d),
    ]
    rows = supertrend_rows + tema_rows

    sections.extend(
        f"| {strategy} | {segment} | {len(values)} |" for strategy, segment, values in rows
    )
    sections.append("")
    sections.extend(
        [
            "### Tickers",
            "| Strategy | Segment | D Recent Buy within W Bull |",
            "|---|---|---|",
        ]
    )
    sections.extend(
        f"| {strategy} | {segment} | {_ticker_cell(values)} |" for strategy, segment, values in rows
    )

    return "\n".join(sections)


def run_mtf_report(
    tight: bool = False,
    report_path: Path | None = None,
    *,
    refresh_data: bool = False,
) -> str:
    report = build_mtf_report(tight=tight, fetch_data_func=get_fetch_data(refresh=refresh_data))
    if report_path is None:
        report_path = shared_report_output_path(datetime.now().strftime("%Y-%m-%d"))
    append_shared_report(report_path, report)
    return str(report_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--tight", action="store_true")
    args = parser.parse_args()
    print(run_mtf_report(tight=args.tight, refresh_data=args.refresh_data))
