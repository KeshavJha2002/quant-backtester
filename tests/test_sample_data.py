from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from trading_bot import utility
from trading_bot.tema_macd.strategy import _tema_macd_state
from trading_bot.utility import (
    MarketDataStore,
    compute_st_trend_from_config,
    config,
    get_fetch_data,
)

FIXTURE_CACHE = Path(__file__).resolve().parent / "fixtures" / "data_cache"


@pytest.fixture(autouse=True)
def forbid_network_download(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_on_network(*args, **kwargs):
        raise AssertionError("Network access is forbidden in deterministic tests")

    monkeypatch.setattr(utility.yf, "download", fail_on_network)


def test_fixture_cache_fetches_without_network() -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    fetch_data = get_fetch_data(store=store)

    data = fetch_data("SAMPLE.NS", start="2024-01-10", type="D")
    timestamps = pd.to_datetime(data["time"], utc=True)

    assert list(data.columns) == ["time", "open", "high", "low", "close", "volume"]
    assert len(data) == 13
    assert timestamps.is_monotonic_increasing
    assert not timestamps.duplicated().any()
    assert data["time"].iloc[0].strftime("%Y-%m-%d") == "2024-01-10"
    np.testing.assert_allclose(float(data["close"].iloc[-1]), 123.0, rtol=1e-10, atol=1e-12)


def test_missing_fixture_with_refresh_would_use_network_boundary() -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)

    with pytest.raises(AssertionError, match="Network access is forbidden"):
        store.fetch_data("MISSING.NS", type="D", refresh=True)


def test_indicators_run_on_fixture_data() -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    data = get_fetch_data(store=store)("SAMPLE.NS", type="D")
    close = np.asarray(data["close"], dtype=float)
    high = np.asarray(data["high"], dtype=float)
    low = np.asarray(data["low"], dtype=float)

    trend = compute_st_trend_from_config(close, high, low, atr_len=3, atr_mult=2.0, smooth_len=1)
    tema, macd, signal, state_before, state_after = _tema_macd_state(
        close,
        {**config, "tema_len": 3, "macd_fast": 3, "macd_slow": 6, "macd_signal": 3},
    )

    assert len(trend) == len(data)
    assert len(tema) == len(data)
    assert len(macd) == len(data)
    assert len(signal) == len(data)
    assert state_before.dtype == bool
    assert state_after.dtype == bool
    np.testing.assert_allclose(trend[-5:], np.array([1, 1, 1, 1, 1]), rtol=1e-10, atol=1e-12)
    assert np.isfinite(macd[-1])
