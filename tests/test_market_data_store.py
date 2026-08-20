from __future__ import annotations

from pathlib import Path

import pandas as pd

from trading_bot.utility.data_store import (
    MarketDataStore,
    get_complete_data,
    get_fetch_data,
    update_universe_cache,
)

FIXTURE_CACHE = Path(__file__).resolve().parent / "fixtures" / "data_cache"


def test_market_data_store_cache_path(tmp_path: Path) -> None:
    store = MarketDataStore(base_dir=tmp_path)
    path_d = store._cache_path("RELIANCE.NS", "D")
    path_w = store._cache_path("RELIANCE.NS", "W")

    assert path_d == tmp_path / "daily" / "RELIANCE.NS.csv"
    assert path_w == tmp_path / "weekly" / "RELIANCE.NS.csv"


def test_market_data_store_read_write(tmp_path: Path) -> None:
    store = MarketDataStore(base_dir=tmp_path)
    df = pd.DataFrame(
        {
            "time": ["2024-01-01", "2024-01-02"],
            "open": [100.0, 105.0],
            "high": [106.0, 110.0],
            "low": [99.0, 104.0],
            "close": [105.0, 108.0],
            "volume": [1000, 1500],
        }
    )

    store._write_cache("TEST.NS", "D", df)
    loaded = store._read_cache("TEST.NS", "D")
    assert loaded is not None
    assert len(loaded) == 2
    assert list(loaded["close"]) == [105.0, 108.0]


def test_get_complete_data_helper() -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    fetcher = get_fetch_data(store=store)

    data, idx = get_complete_data(fetcher, "SAMPLE.NS", "D")
    assert len(data) > 0
    assert idx == len(data) - 1


def test_update_universe_cache_mocked(tmp_path: Path, monkeypatch) -> None:
    store = MarketDataStore(base_dir=tmp_path)
    mock_df = pd.DataFrame(
        {
            "time": ["2024-01-01"],
            "open": [100.0],
            "high": [105.0],
            "low": [99.0],
            "close": [102.0],
            "volume": [1000],
        }
    )
    monkeypatch.setattr(store, "_download", lambda ticker, start, type: mock_df)

    res = update_universe_cache(["TEST1.NS", "TEST2.NS"], intervals=("D", "W"), store=store)
    assert "TEST1.NS" in res
    assert res["TEST1.NS"]["D"] is True
    assert res["TEST1.NS"]["W"] is True
    assert store._cache_path("TEST1.NS", "D").exists()
