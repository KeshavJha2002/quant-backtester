from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    analyze_projection_cone,
    get_sigma_bucket,
)
from trading_bot.utility import (
    UNIVERSES,
    ensure_output_dir,
    get_complete_data,
    get_fetch_data,
)

__all__ = [
    "UNIVERSES",
    "StrategyContext",
    "StrategyReportSection",
    "get_fetcher",
    "get_complete_bar_fetcher",
    "build_strategy_section",
    "write_section_report",
    "build_combined_report_filename",
    "render_combined_report",
    "ticker_cell",
    "scan_projection_cone_latest",
    "_sigma_bucket",
]


@dataclass(frozen=True)
class StrategyContext:
    refresh_data: bool = False
    tight: bool = False
    min_negative_sigma: float = -1.0


@dataclass(frozen=True)
class StrategyReportSection:
    mode: str
    strategy_number: int
    title: str
    content: str


def get_fetcher(refresh_data: bool) -> Callable[[str, str, str], pd.DataFrame]:
    """Get market data fetcher with specified refresh policy."""
    return get_fetch_data(refresh=refresh_data)


def get_complete_bar_fetcher(
    base_fetcher: Callable[..., pd.DataFrame],
) -> Callable[..., pd.DataFrame]:
    """Wrap a data fetcher to automatically truncate data to the latest complete bar."""

    def _fetcher(ticker: str, *, type: str = "W", start: str = "1990-01-01") -> pd.DataFrame:
        data, _ = get_complete_data(base_fetcher, ticker, type)
        return data

    return _fetcher


def build_strategy_section(
    mode: str, strategy_number: int, title: str, content: str
) -> StrategyReportSection:
    """Build a report section object for a strategy."""
    return StrategyReportSection(
        mode=mode,
        strategy_number=strategy_number,
        title=title,
        content=content,
    )


def write_section_report(section: StrategyReportSection) -> str:
    """Write an individual strategy report section to disk under report/<date>/."""
    report_date = datetime.now().strftime("%Y-%m-%d")
    output_dir = ensure_output_dir("report", report_date)
    output_path = output_dir / build_combined_report_filename(
        section.mode, [section.strategy_number]
    )
    output_path.write_text(render_combined_report([section]), encoding="utf-8")
    return str(output_path)


def build_combined_report_filename(mode: str, strategy_numbers: list[int]) -> str:
    """Build standardized report filename for given mode and list of strategy numbers."""
    ordered = sorted(dict.fromkeys(strategy_numbers))
    strategy_token = "_".join(str(value) for value in ordered)
    return f"{mode}_{strategy_token}.md"


def render_combined_report(sections: list[StrategyReportSection]) -> str:
    """Render multiple strategy report sections into a single markdown document."""
    generated_at = datetime.now().isoformat(timespec="seconds")
    lines = [
        "# Strategy Runner Report",
        f"- Generated: `{generated_at}`",
        "",
    ]
    for section in sections:
        lines.extend(
            [
                f"## {section.title}",
                f"- Generated: `{generated_at}`",
                "",
                section.content,
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def ticker_cell(values: list[str]) -> str:
    """Format a list of tickers as a backticked comma-separated cell in a markdown table."""
    return ", ".join(f"`{value}`" for value in values) if values else "-"


def scan_projection_cone_latest(
    tickers: list[str],
    fetch_data_func: Callable[..., pd.DataFrame],
    *,
    segment: str,
    freq: str,
    cone_config: ProjectionConeConfig | None = None,
) -> list[dict[str, Any]]:
    """Scan tickers for latest projection cone status."""
    cone_config = cone_config or ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        try:
            result = analyze_projection_cone(
                ticker,
                fetch_data_func=fetch_data_func,
                freq=freq,
                config=cone_config,
            )
            rows.append(
                {
                    "segment": segment,
                    "ticker": ticker,
                    "bar_time": result["as_of"],
                    "current_price": result["current_price"],
                    "sigma_move": result["zone"]["sigma_move"],
                    "sigma_bucket": get_sigma_bucket(result["zone"]["sigma_move"], unicode_symbol=True),
                    "price_zone": result["zone"]["name"],
                    "anchor_type": result["anchor"]["type"],
                    "anchor_price": result["anchor"]["price"],
                }
            )
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")
    return rows


# Backward-compatible alias
_sigma_bucket = get_sigma_bucket
