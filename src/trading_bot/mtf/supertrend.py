from __future__ import annotations

from collections.abc import Iterable

from trading_bot.supertrend.strategy import run_supertrend_scans


def run_supertrend_mtf_scan(
    tickers: Iterable[str],
    fetch_data_func,
) -> tuple[list[str], list[str]]:
    _, daily_recent, _ = run_supertrend_scans(tickers, fetch_data_func, "D", mode="pullback")
    weekly_bull, _, _ = run_supertrend_scans(tickers, fetch_data_func, "W", mode="or")

    weekly_bullish = weekly_bull["W"]
    weekly_bullish_set = set(weekly_bullish)
    daily_filtered = [ticker for ticker in daily_recent["D"] if ticker in weekly_bullish_set]

    return daily_filtered, weekly_bullish
