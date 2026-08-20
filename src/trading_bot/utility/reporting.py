from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]


def ensure_output_dir(*parts: str) -> Path:
    """Ensure a directory path relative to the project root exists and return it."""
    path = PROJECT_ROOT.joinpath(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamped_output_path(strategy_name: str, suffix: str = ".txt") -> Path:
    """Generate a timestamped filepath under <strategy_name>/outputs/."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = ensure_output_dir(strategy_name, "outputs")
    return output_dir / f"{timestamp}{suffix}"


def shared_report_output_path(report_date: str, suffix: str = ".md") -> Path:
    """Generate a filepath under reports/ for the given date."""
    output_dir = ensure_output_dir("reports")
    return output_dir / f"{report_date}{suffix}"


def initialize_shared_report(report_path: Path, title: str, generated_at: str) -> None:
    """Initialize a markdown shared report with title and generation timestamp."""
    report = "\n".join(
        [
            f"# {title}",
            f"- Generated: `{generated_at}`",
            "",
        ]
    )
    report_path.write_text(report, encoding="utf-8")


def append_shared_report(report_path: Path, content: str) -> None:
    """Append text content to a report file."""
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(content if content.endswith("\n") else f"{content}\n")


def latest_data_date(
    ticker: str,
    fetch_data_func: Callable[..., Any] | None = None,
    freq: str = "D",
) -> str:
    """Return the formatted date of the most recent candle in the dataset."""
    from trading_bot.utility.data_store import fetch_data

    fetcher = fetch_data_func or fetch_data
    data = fetcher(ticker, type=freq)
    import pandas as pd

    last_value = pd.to_datetime(data["time"].iloc[-1])
    return str(last_value.strftime("%Y-%m-%d"))
