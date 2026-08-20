from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from research.experiments.optimize_supertrend_cone import (
    StrategyVariant,
    compute_trade_metrics,
    run_supertrend_cone_variant,
)
from trading_bot.utility import (
    MarketDataStore,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="N150", choices=["N150", "N250", "N50", "all"])
    parser.add_argument("--min-negative-sigma", type=float, default=0.0)
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--range", dest="range_value", default="all")
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()

    variant = StrategyVariant(
        name="C7 Elite Quantum Supertrend MTF + Cone Discount",
        max_sigma=args.min_negative_sigma,
        require_sma200=True,
        require_volume=True,
        require_adx=True,
        exit_mode="cone_target",
    )

    store = MarketDataStore()
    fetcher = get_fetch_data(refresh=args.refresh_data, store=store)

    target_universes = (
        ["N150"]
        if args.universe == "N150"
        else (["N150", "N250", "N50"] if args.universe == "all" else [args.universe])
    )

    for univ in target_universes:
        tickers = (
            nifty150_ns
            if univ == "N150"
            else (nifty250_ns if univ == "N250" else nifty50_ns)
        )
        all_trades = []

        def _run(ticker: str) -> list:
            try:
                d_df = fetcher(ticker, type="D")
                w_df = fetcher(ticker, type="W")
                return run_supertrend_cone_variant(d_df, w_df, ticker, variant)
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {executor.submit(_run, ticker): ticker for ticker in tickers}
            for f in as_completed(futures):
                all_trades.extend(f.result())

        m = compute_trade_metrics(all_trades, strategy_name=variant.name, universe=univ)
        print(f"\n=== Combination Strategy 7 ({univ}) ===")
        print(f"Trade Count: {m.trade_count}")
        print(f"Win Rate: {m.win_rate_pct}%")
        print(f"Profit Factor: {m.profit_factor}")
        print(f"Average Return: {m.avg_return_pct}%")
        print(f"Median Duration: {m.median_duration_days} days")
        print(f"Max Drawdown: {m.max_drawdown_pct}%")
        print(f"Sharpe Ratio: {m.sharpe_ratio}")


if __name__ == "__main__":
    main()
