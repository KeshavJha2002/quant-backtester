from __future__ import annotations

import argparse

from research.support.trend_supertrend_suite import print_mtf_performance
from trading_bot.utility import get_fetch_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()
    print_mtf_performance(fetch_data_func=get_fetch_data(refresh=args.refresh_data))
