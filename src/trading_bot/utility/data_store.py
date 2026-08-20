from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import yfinance as yf

from trading_bot.utility.reporting import ensure_output_dir
from trading_bot.utility.timing import latest_complete_bar_index

if TYPE_CHECKING:
    pass


class MarketDataStore:
    """Manages cached and downloaded OHLCV market data for NSE equities."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or ensure_output_dir("data_cache")
        self._lock = threading.Lock()

    def _cache_path(self, ticker: str, type: str) -> Path:
        interval_dir = self.base_dir / ("daily" if type == "D" else "weekly")
        interval_dir.mkdir(parents=True, exist_ok=True)
        safe_ticker = ticker.replace("/", "_")
        return interval_dir / f"{safe_ticker}.csv"

    def _read_cache(self, ticker: str, type: str) -> pd.DataFrame | None:
        cache_path = self._cache_path(ticker, type)
        if not cache_path.exists():
            return None

        df = pd.read_csv(cache_path, parse_dates=["time"])
        if df.empty:
            return None
        return df[["time", "open", "high", "low", "close", "volume"]]

    def _download(self, ticker: str, start: str, type: str) -> pd.DataFrame:
        last_error = None
        for attempt in range(3):
            try:
                with self._lock:
                    df = yf.download(
                        tickers=ticker,
                        start=start,
                        interval="1d" if type == "D" else "1wk",
                        auto_adjust=False,
                        progress=False,
                    )
                if df.empty:
                    raise ValueError(f"No data returned for ticker {ticker}")

                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                df = df.reset_index()
                df.columns = [str(c) for c in df.columns]
                df = df.rename(
                    columns={
                        "Date": "time",
                        "Open": "open",
                        "High": "high",
                        "Low": "low",
                        "Close": "close",
                        "Volume": "volume",
                    }
                )
                df["time"] = pd.to_datetime(df["time"])
                return df[["time", "open", "high", "low", "close", "volume"]]
            except AssertionError:
                raise
            except Exception as exc:
                last_error = exc
                time.sleep(0.3 * (attempt + 1))

        raise ValueError(f"Failed to download data for {ticker} after retries: {last_error}")

    def _write_cache(self, ticker: str, type: str, df: pd.DataFrame) -> None:
        cache_path = self._cache_path(ticker, type)
        df.to_csv(cache_path, index=False)

    def fetch_data(
        self,
        ticker: str,
        start: str = "1990-01-01",
        type: str = "W",
        *,
        refresh: bool = False,
    ) -> pd.DataFrame:
        """Fetch OHLCV market data for ticker, reading from cache or downloading as needed."""
        cached = None if refresh else self._read_cache(ticker, type)
        if cached is None:
            cached = self._download(ticker, start, type)
            self._write_cache(ticker, type, cached)

        time_series = pd.to_datetime(cached["time"])
        filtered = cached[time_series >= pd.Timestamp(start)].copy()
        if filtered.empty:
            raise ValueError(f"No cached data returned for ticker {ticker} from {start}")
        return filtered.reset_index(drop=True)


default_data_store: MarketDataStore = MarketDataStore()


def fetch_data(
    ticker: str,
    start: str = "1990-01-01",
    type: str = "W",
    *,
    refresh: bool = False,
) -> pd.DataFrame:
    """Fetch market data using the default data store."""
    return default_data_store.fetch_data(ticker, start=start, type=type, refresh=refresh)


def get_fetch_data(
    *,
    refresh: bool = False,
    store: MarketDataStore | None = None,
) -> Callable[[str, str, str], pd.DataFrame]:
    """Return a data fetcher callable configured with the specified cache policy."""
    active_store = store or default_data_store

    def _fetcher(ticker: str, start: str = "1990-01-01", type: str = "W") -> pd.DataFrame:
        return active_store.fetch_data(ticker, start=start, type=type, refresh=refresh)

    return _fetcher


def get_complete_data(
    fetch_data_func: Callable[..., pd.DataFrame],
    ticker: str,
    freq: str,
) -> tuple[pd.DataFrame, int]:
    """Fetch market data sliced up to the latest fully completed bar index."""
    data = fetch_data_func(ticker, type=freq).reset_index(drop=True)
    idx = latest_complete_bar_index(np.asarray(data["time"].values), freq)
    if idx is None or idx <= 0:
        raise ValueError(f"No complete {freq} bar available for {ticker}")
    return data.iloc[: idx + 1].reset_index(drop=True), idx


def update_universe_cache(
    tickers: Iterable[str],
    intervals: tuple[str, ...] = ("D", "W"),
    max_workers: int = 8,
    store: MarketDataStore | None = None,
) -> dict[str, dict[str, bool]]:
    """Concurrently refresh local cache for given tickers and intervals."""
    active_store = store or default_data_store
    results: dict[str, dict[str, bool]] = {}

    tasks: list[tuple[str, str]] = [
        (ticker, interval) for ticker in tickers for interval in intervals
    ]

    def _update(ticker: str, interval: str) -> tuple[str, str, bool, str | None]:
        try:
            active_store.fetch_data(ticker, type=interval, refresh=True)
            return ticker, interval, True, None
        except Exception as exc:
            return ticker, interval, False, str(exc)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(_update, ticker, interval) for ticker, interval in tasks]
        for future in as_completed(futures):
            ticker, interval, success, error_msg = future.result()
            if ticker not in results:
                results[ticker] = {}
            results[ticker][interval] = success
            if not success:
                print(f"[Warning] Failed to refresh {ticker} ({interval}): {error_msg}")

    return results
