from __future__ import annotations

import pandas as pd

from trading_bot.utility.timing import (
    _latest_complete_bar_index,
    latest_complete_bar_index,
)


def test_latest_complete_bar_empty() -> None:
    assert latest_complete_bar_index([], "D") is None
    assert latest_complete_bar_index([], "W") is None


def test_latest_complete_bar_historical_daily() -> None:
    # All dates in the past should return the last index
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    idx = latest_complete_bar_index(dates, "D")
    assert idx == 9


def test_latest_complete_bar_historical_weekly() -> None:
    # All dates in the past should return the last index
    dates = pd.date_range("2024-01-01", periods=10, freq="W")
    idx = latest_complete_bar_index(dates, "W")
    assert idx == 9


def test_latest_complete_bar_alias_compatibility() -> None:
    dates = pd.date_range("2024-01-01", periods=5, freq="D")
    assert latest_complete_bar_index(dates, "D") == _latest_complete_bar_index(dates, "D")
