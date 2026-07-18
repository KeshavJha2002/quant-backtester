from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from trading_bot.projection_cone import ProjectionConeConfig, analyze_projection_cone
from trading_bot.utility import (
    ensure_output_dir,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


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


UNIVERSES: list[tuple[str, list[str]]] = [
    ("N50", nifty50_ns),
    ("N150", nifty150_ns),
    ("N250", nifty250_ns),
]


def get_fetcher(refresh_data: bool):
    return get_fetch_data(refresh=refresh_data)


def build_strategy_section(
    mode: str, strategy_number: int, title: str, content: str
) -> StrategyReportSection:
    return StrategyReportSection(
        mode=mode,
        strategy_number=strategy_number,
        title=title,
        content=content,
    )


def write_section_report(section: StrategyReportSection) -> str:
    report_date = datetime.now().strftime("%Y-%m-%d")
    output_dir = ensure_output_dir("report", report_date)
    output_path = output_dir / build_combined_report_filename(
        section.mode, [section.strategy_number]
    )
    output_path.write_text(render_combined_report([section]), encoding="utf-8")
    return str(output_path)


def build_combined_report_filename(mode: str, strategy_numbers: list[int]) -> str:
    ordered = sorted(dict.fromkeys(strategy_numbers))
    strategy_token = "_".join(str(value) for value in ordered)
    return f"{mode}_{strategy_token}.md"


def render_combined_report(sections: list[StrategyReportSection]) -> str:
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
    return ", ".join(f"`{value}`" for value in values) if values else "-"


def scan_projection_cone_latest(
    tickers: list[str],
    fetch_data_func,
    *,
    segment: str,
    freq: str,
    cone_config: ProjectionConeConfig | None = None,
) -> list[dict[str, Any]]:
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
                    "sigma_bucket": _sigma_bucket(result["zone"]["sigma_move"]),
                    "price_zone": result["zone"]["name"],
                    "anchor_type": result["anchor"]["type"],
                    "anchor_price": result["anchor"]["price"],
                }
            )
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")
    return rows


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
