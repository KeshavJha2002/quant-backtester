from __future__ import annotations

from pathlib import Path

import pytest
from research.support.cone_backtest import append_trade, metrics_from_trades, sigma_bucket
from research.support.selection import (
    apply_safe_slice,
    parse_range_arg,
    parse_universe_arg,
    slice_label,
    update_slice_report,
)


def test_selection_parse_universe() -> None:
    assert parse_universe_arg("all") == ["N50", "N150", "N250"]
    assert parse_universe_arg("N50") == ["N50"]
    assert parse_universe_arg("n150") == ["N150"]

    with pytest.raises(ValueError, match="universe must be"):
        parse_universe_arg("INVALID")


def test_selection_parse_range() -> None:
    assert parse_range_arg("all") is None
    assert parse_range_arg("0,10") == (0, 10)
    assert parse_range_arg("10,0") == (0, 10)

    with pytest.raises(ValueError, match="range must be"):
        parse_range_arg("invalid")


def test_selection_apply_safe_slice() -> None:
    items = ["A", "B", "C", "D", "E"]
    sliced, bounds = apply_safe_slice(items, (1, 3))
    assert sliced == ["B", "C", "D"]
    assert bounds == (1, 3)

    # Clamping
    sliced_clamp, bounds_clamp = apply_safe_slice(items, (-5, 100))
    assert sliced_clamp == items
    assert bounds_clamp == (0, 4)

    # All
    sliced_all, bounds_all = apply_safe_slice(items, None)
    assert sliced_all == items
    assert bounds_all is None


def test_slice_label() -> None:
    assert slice_label("N50", None) == "N50"
    assert slice_label("N50", (0, 10)) == "N50 [0,10]"


def test_update_slice_report(tmp_path: Path) -> None:
    report_file = tmp_path / "test_report.md"
    update_slice_report(report_file, "N50_all", "Sample Content", "Test Suite")
    content = report_file.read_text(encoding="utf-8")
    assert "<!-- BEGIN N50_all -->" in content
    assert "Sample Content" in content
    assert "<!-- END N50_all -->" in content


def test_cone_backtest_metrics() -> None:
    trades: list[dict[str, float]] = []
    append_trade(
        trades,
        entry_price=100.0,
        exit_price=110.0,
        entry_time="2024-01-01",
        exit_time="2024-01-10",
        sigma_move=-1.5,
        sigma_bucket_value=sigma_bucket(-1.5),
    )
    append_trade(
        trades,
        entry_price=100.0,
        exit_price=95.0,
        entry_time="2024-01-01",
        exit_time="2024-01-05",
        sigma_move=-0.5,
        sigma_bucket_value=sigma_bucket(-0.5),
    )

    metrics = metrics_from_trades(trades, "Test Label")
    assert metrics["trade_count"] == 2.0
    assert metrics["avg_return_pct"] == pytest.approx(2.5)
    assert metrics["win_rate_pct"] == pytest.approx(50.0)
    assert metrics["median_duration_days"] == pytest.approx(6.5)
