from __future__ import annotations

from collections.abc import Callable, Iterable

import pandas as pd

from trading_bot.tema_macd.strategy import (
    tema_macd_active_bull_screen,
    tema_macd_fresh_bull_screen,
    tema_macd_fresh_bull_screen_tight,
)


def run_tema_macd_mtf_scan(
    tickers: Iterable[str],
    fetch_data_func: Callable[..., pd.DataFrame],
    config: dict[str, int],
    *,
    tight: bool = True,
) -> tuple[list[str], list[str]]:
    """Scan tickers for daily TEMA-MACD fresh buy signals confirmed by weekly active bullish state."""
    scanner = tema_macd_fresh_bull_screen_tight if tight else tema_macd_fresh_bull_screen

    daily_signals = scanner(tickers, fetch_data_func, "D", config)
    weekly_signals = tema_macd_active_bull_screen(tickers, fetch_data_func, "W", config)

    weekly_signal_set = set(weekly_signals)
    daily_filtered = [ticker for ticker in daily_signals if ticker in weekly_signal_set]

    return daily_filtered, weekly_signals
