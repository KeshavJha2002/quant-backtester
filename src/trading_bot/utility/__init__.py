from __future__ import annotations

import yfinance as yf

from trading_bot.utility.data_store import (
    MarketDataStore,
    default_data_store,
    fetch_data,
    get_complete_data,
    get_fetch_data,
    update_universe_cache,
)
from trading_bot.utility.indicators import (
    compute_st_trend_from_config,
    compute_triple_supertrend,
    config,
    ema,
    rma,
    rsi,
    sma,
    st_config,
    true_range,
)
from trading_bot.utility.reporting import (
    PROJECT_ROOT,
    append_shared_report,
    ensure_output_dir,
    initialize_shared_report,
    latest_data_date,
    shared_report_output_path,
    timestamped_output_path,
)
from trading_bot.utility.timing import (
    MARKET_CLOSE,
    MARKET_TZ,
    _latest_complete_bar_index,
    latest_complete_bar_index,
)
from trading_bot.utility.universe import (
    UNIVERSE_MAP,
    UNIVERSES,
    detect_universe,
    nifty50,
    nifty50_ns,
    nifty150,
    nifty150_ns,
    nifty250,
    nifty250_ns,
    normalize_ticker,
)

__all__ = [
    # Universe
    "nifty50",
    "nifty150",
    "nifty250",
    "nifty50_ns",
    "nifty150_ns",
    "nifty250_ns",
    "UNIVERSE_MAP",
    "UNIVERSES",
    "normalize_ticker",
    "detect_universe",
    # Indicators & Config
    "config",
    "st_config",
    "true_range",
    "rma",
    "sma",
    "ema",
    "rsi",
    "compute_st_trend_from_config",
    "compute_triple_supertrend",
    # Timing
    "MARKET_TZ",
    "MARKET_CLOSE",
    "latest_complete_bar_index",
    "_latest_complete_bar_index",
    # Data store
    "MarketDataStore",
    "default_data_store",
    "fetch_data",
    "get_fetch_data",
    "get_complete_data",
    "update_universe_cache",
    "yf",
    # Reporting
    "PROJECT_ROOT",
    "ensure_output_dir",
    "timestamped_output_path",
    "latest_data_date",
    "shared_report_output_path",
    "initialize_shared_report",
    "append_shared_report",
]
