from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from research.support.cone_backtest import entry_sigma_move

from trading_bot.projection_cone import ProjectionConeConfig
from trading_bot.tema_macd.strategy import _tema_macd_state
from trading_bot.utility import (
    compute_st_trend_from_config,
    config,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)

ENTRY_CAPITAL = 10_000.0
LIMITED_CAPITAL = 400_000.0
DEFAULT_CONE_THRESHOLD = 1.0
WEEKLY_NEW_TRADE_CAP = 5
ACTIVE_STRATEGIES = ("c5_ww", "c6_d", "c6_w")

UNIVERSES = {
    "N50": nifty50_ns,
    "N150": nifty150_ns,
    "N250": nifty250_ns,
}

ALL_TICKERS: list[tuple[str, str]] = [
    (segment, ticker) for segment, tickers in UNIVERSES.items() for ticker in tickers
]

HOLDING_DAY_PROXY = {
    "c5_dw": 25.0,
    "c5_ww": 98.0,
    "c6_d": 70.0,
    "c6_w": 450.0,
}

QUALITY_WEIGHT = {
    "c5_dw": 1.00,
    "c5_ww": 0.95,
    "c6_d": 0.90,
    "c6_w": 0.85,
}


@dataclass(frozen=True)
class TradeCandidate:
    strategy: str
    segment: str
    ticker: str
    timeframe: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    sigma_move: float
    score: float

    @property
    def shares(self) -> float:
        return ENTRY_CAPITAL / self.entry_price

    @property
    def proceeds(self) -> float:
        return self.shares * self.exit_price

    @property
    def pnl(self) -> float:
        return self.proceeds - ENTRY_CAPITAL

    @property
    def return_pct(self) -> float:
        return self.pnl / ENTRY_CAPITAL * 100.0

    @property
    def duration_days(self) -> float:
        return float((pd.to_datetime(self.exit_time) - pd.to_datetime(self.entry_time)).total_seconds() / 86400.0)


@dataclass
class OpenPosition:
    trade: TradeCandidate


def _build_score(strategy: str, sigma_move: float, threshold: float) -> float:
    # Deeper cone discount is better. Faster turnover gets a boost through the holding proxy.
    sigma_edge = max(0.01, threshold - sigma_move)
    return QUALITY_WEIGHT[strategy] * sigma_edge / HOLDING_DAY_PROXY[strategy]


def _weekly_state_series(weekly_data: pd.DataFrame) -> pd.DataFrame:
    weekly_close = np.asarray(weekly_data["close"].values, dtype=float).ravel()
    _, _, _, _, state_after = _tema_macd_state(weekly_close, config)

    sigma_values: list[float | None] = []
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False, bars_per_year=52)
    weekly_high = np.asarray(weekly_data["high"].values, dtype=float).ravel()
    weekly_low = np.asarray(weekly_data["low"].values, dtype=float).ravel()
    for idx in range(len(weekly_close)):
        if idx == 0:
            sigma_values.append(None)
            continue
        sigma_values.append(
            entry_sigma_move(weekly_close, weekly_high, weekly_low, idx, "W", cone_config)
        )

    return pd.DataFrame(
        {
            "time": pd.to_datetime(weekly_data["time"].values),
            "weekly_bull": state_after.astype(bool),
            "weekly_sigma": sigma_values,
        }
    ).sort_values("time")


def generate_c5_dw_trades(
    daily_data: pd.DataFrame, weekly_data: pd.DataFrame, segment: str, ticker: str, threshold: float
) -> list[TradeCandidate]:
    daily_close = np.asarray(daily_data["close"].values, dtype=float).ravel()
    daily_time = pd.to_datetime(daily_data["time"].values)
    daily_tema, daily_macd, daily_signal, daily_state_before, _ = _tema_macd_state(
        daily_close, config
    )

    weekly_state = _weekly_state_series(weekly_data)
    daily_frame = pd.DataFrame({"time": daily_time}).sort_values("time")
    aligned = pd.merge_asof(daily_frame, weekly_state, on="time", direction="backward")
    weekly_bull = aligned["weekly_bull"].fillna(False).to_numpy(dtype=bool)
    weekly_sigma = aligned["weekly_sigma"].to_numpy()

    trades: list[TradeCandidate] = []
    in_position = False
    entry_idx: int | None = None
    entry_sigma = 0.0

    for idx in range(1, len(daily_close)):
        if np.isnan(daily_tema[idx]) or np.isnan(daily_macd[idx]) or np.isnan(daily_signal[idx]):
            continue

        fresh_buy = (
            daily_tema[idx] >= daily_tema[idx - 1]
            and not daily_state_before[idx]
            and daily_macd[idx] >= daily_signal[idx]
        )
        fresh_sell = (
            daily_tema[idx] < daily_tema[idx - 1]
            and daily_state_before[idx]
            and daily_macd[idx] < daily_signal[idx]
        )
        sigma_value = weekly_sigma[idx]
        buy_cond = (
            fresh_buy
            and weekly_bull[idx]
            and pd.notna(sigma_value)
            and float(sigma_value) < threshold
        )

        if not in_position and buy_cond:
            in_position = True
            entry_idx = idx
            entry_sigma = float(sigma_value)
            continue

        if in_position and fresh_sell and entry_idx is not None:
            trades.append(
                TradeCandidate(
                    strategy="c5_dw",
                    segment=segment,
                    ticker=ticker,
                    timeframe="D",
                    entry_time=daily_time[entry_idx],
                    exit_time=daily_time[idx],
                    entry_price=float(daily_close[entry_idx]),
                    exit_price=float(daily_close[idx]),
                    sigma_move=entry_sigma,
                    score=_build_score("c5_dw", entry_sigma, threshold),
                )
            )
            in_position = False
            entry_idx = None

    return trades


def generate_c5_ww_trades(
    weekly_data: pd.DataFrame, segment: str, ticker: str, threshold: float
) -> list[TradeCandidate]:
    weekly_close = np.asarray(weekly_data["close"].values, dtype=float).ravel()
    weekly_high = np.asarray(weekly_data["high"].values, dtype=float).ravel()
    weekly_low = np.asarray(weekly_data["low"].values, dtype=float).ravel()
    weekly_time = pd.to_datetime(weekly_data["time"].values)
    weekly_tema, weekly_macd, weekly_signal, weekly_state_before, _ = _tema_macd_state(
        weekly_close, config
    )
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False, bars_per_year=52)

    trades: list[TradeCandidate] = []
    in_position = False
    entry_idx: int | None = None
    entry_sigma = 0.0

    for idx in range(1, len(weekly_close)):
        if np.isnan(weekly_tema[idx]) or np.isnan(weekly_macd[idx]) or np.isnan(weekly_signal[idx]):
            continue
        fresh_buy = (
            weekly_tema[idx] >= weekly_tema[idx - 1]
            and not weekly_state_before[idx]
            and weekly_macd[idx] >= weekly_signal[idx]
        )
        fresh_sell = (
            weekly_tema[idx] < weekly_tema[idx - 1]
            and weekly_state_before[idx]
            and weekly_macd[idx] < weekly_signal[idx]
        )
        sigma_value = entry_sigma_move(weekly_close, weekly_high, weekly_low, idx, "W", cone_config)
        buy_cond = fresh_buy and sigma_value is not None and sigma_value < threshold

        if not in_position and buy_cond:
            in_position = True
            entry_idx = idx
            entry_sigma = float(sigma_value)
            continue

        if in_position and fresh_sell and entry_idx is not None:
            trades.append(
                TradeCandidate(
                    strategy="c5_ww",
                    segment=segment,
                    ticker=ticker,
                    timeframe="W",
                    entry_time=weekly_time[entry_idx],
                    exit_time=weekly_time[idx],
                    entry_price=float(weekly_close[entry_idx]),
                    exit_price=float(weekly_close[idx]),
                    sigma_move=entry_sigma,
                    score=_build_score("c5_ww", entry_sigma, threshold),
                )
            )
            in_position = False
            entry_idx = None

    return trades


def generate_c6_trades(
    data: pd.DataFrame, segment: str, ticker: str, freq: str, threshold: float
) -> list[TradeCandidate]:
    close = np.asarray(data["close"].values, dtype=float).ravel()
    high = np.asarray(data["high"].values, dtype=float).ravel()
    low = np.asarray(data["low"].values, dtype=float).ravel()
    time_values = pd.to_datetime(data["time"].values)

    trend1 = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend2 = compute_st_trend_from_config(close, high, low, 14, 3.0, 2)
    trend3 = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)
    cone_config = ProjectionConeConfig(
        lock_mode=True, lock_to_bull=False, bars_per_year=252 if freq == "D" else 52
    )

    trades: list[TradeCandidate] = []
    in_position = False
    entry_idx: int | None = None
    entry_sigma = 0.0

    for idx in range(1, len(close)):
        fresh_buy = (
            (trend1[idx - 1] == -1 and trend1[idx] == 1)
            or (trend2[idx - 1] == -1 and trend2[idx] == 1)
            or (trend3[idx - 1] == -1 and trend3[idx] == 1)
        )
        regime_bull = trend1[idx] == 1 or trend2[idx] == 1 or trend3[idx] == 1
        sigma_value = entry_sigma_move(close, high, low, idx, freq, cone_config)
        buy_cond = fresh_buy and sigma_value is not None and sigma_value < threshold

        if not in_position and buy_cond:
            in_position = True
            entry_idx = idx
            entry_sigma = float(sigma_value)
            continue

        if in_position and not regime_bull and entry_idx is not None:
            trades.append(
                TradeCandidate(
                    strategy="c6_d" if freq == "D" else "c6_w",
                    segment=segment,
                    ticker=ticker,
                    timeframe=freq,
                    entry_time=time_values[entry_idx],
                    exit_time=time_values[idx],
                    entry_price=float(close[entry_idx]),
                    exit_price=float(close[idx]),
                    sigma_move=entry_sigma,
                    score=_build_score("c6_d" if freq == "D" else "c6_w", entry_sigma, threshold),
                )
            )
            in_position = False
            entry_idx = None

    return trades


def load_trade_candidates(
    fetch_data_func, threshold: float
) -> tuple[list[TradeCandidate], dict[str, tuple[np.ndarray, np.ndarray]]]:
    trades: list[TradeCandidate] = []
    price_cache: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    total = len(ALL_TICKERS)

    for index, (segment, ticker) in enumerate(ALL_TICKERS, start=1):
        print(f"[{index}/{total}] Processing {ticker} ({segment})")
        try:
            daily_data = fetch_data_func(ticker, type="D")
            weekly_data = fetch_data_func(ticker, type="W")
        except Exception as exc:
            print(f"Skipping {ticker}: {exc}")
            continue

        price_cache[ticker] = (
            pd.to_datetime(daily_data["time"].values).to_numpy(),
            np.asarray(daily_data["close"].values, dtype=float).ravel(),
        )

        print(f"  - generating c5_ww trades for {ticker}")
        c5_ww_trades = generate_c5_ww_trades(weekly_data, segment, ticker, threshold)
        print(f"    generated {len(c5_ww_trades)} trades")

        print(f"  - generating c6_d trades for {ticker}")
        c6_d_trades = generate_c6_trades(daily_data, segment, ticker, "D", threshold)
        print(f"    generated {len(c6_d_trades)} trades")

        print(f"  - generating c6_w trades for {ticker}")
        c6_w_trades = generate_c6_trades(weekly_data, segment, ticker, "W", threshold)
        print(f"    generated {len(c6_w_trades)} trades")

        strategy_trades: dict[str, list[TradeCandidate]] = {
            # "c5_dw": generate_c5_dw_trades(daily_data, weekly_data, segment, ticker, threshold),
            "c5_ww": c5_ww_trades,
            "c6_d": c6_d_trades,
            "c6_w": c6_w_trades,
        }
        for strategy in ACTIVE_STRATEGIES:
            trades.extend(strategy_trades[strategy])
        print(f"  - cumulative trades so far: {len(trades)}")

    return trades, price_cache


def get_close_asof(
    price_cache: dict[str, tuple[np.ndarray, np.ndarray]], ticker: str, timestamp: pd.Timestamp
) -> float:
    dates, closes = price_cache[ticker]
    target = np.datetime64(timestamp.normalize())
    idx = np.searchsorted(dates, target, side="right") - 1
    if idx < 0:
        idx = 0
    return float(closes[idx])


def _week_key(ts: pd.Timestamp) -> tuple[int, int]:
    iso = ts.isocalendar()
    return int(iso.year), int(iso.week)


def simulate_portfolio(
    trades: list[TradeCandidate],
    price_cache: dict[str, tuple[np.ndarray, np.ndarray]],
    *,
    capital_limit: float | None,
) -> dict[str, Any]:
    entry_events: dict[pd.Timestamp, list[TradeCandidate]] = defaultdict(list)
    exit_events: dict[pd.Timestamp, list[TradeCandidate]] = defaultdict(list)
    all_dates: set[pd.Timestamp] = set()

    for trade in trades:
        entry_day = trade.entry_time.normalize()
        exit_day = trade.exit_time.normalize()
        entry_events[entry_day].append(trade)
        exit_events[exit_day].append(trade)
        all_dates.add(entry_day)
        all_dates.add(exit_day)

    for dates, _ in price_cache.values():
        for value in dates:
            all_dates.add(pd.Timestamp(value).normalize())

    timeline = sorted(all_dates)
    cash = 0.0 if capital_limit is None else capital_limit
    open_positions: dict[tuple[str, str, pd.Timestamp], OpenPosition] = {}
    executed_trades: list[TradeCandidate] = []
    skipped_trades: list[TradeCandidate] = []
    weekly_open_counts: dict[tuple[int, int], int] = defaultdict(int)
    max_deployed = 0.0
    daily_rows: list[dict[str, Any]] = []
    realized_pnl = 0.0
    baseline_capital = capital_limit if capital_limit is not None else 0.0

    for current_day in timeline:
        for trade in exit_events.get(current_day, []):
            key = (trade.strategy, trade.ticker, trade.entry_time)
            position = open_positions.pop(key, None)
            if position is None:
                continue
            cash += trade.proceeds
            realized_pnl += trade.pnl

        daily_candidates = []
        weekly_candidates = []
        for trade in entry_events.get(current_day, []):
            if trade.timeframe == "W":
                weekly_candidates.append(trade)
            else:
                daily_candidates.append(trade)

        daily_candidates.sort(key=lambda trade: (-trade.score, trade.sigma_move, trade.ticker))
        weekly_candidates.sort(key=lambda trade: (-trade.score, trade.sigma_move, trade.ticker))

        def maybe_open(
            trade: TradeCandidate,
            *,
            enforce_weekly_cap: bool,
            trading_day: pd.Timestamp,
        ) -> None:
            nonlocal cash, max_deployed
            week_key = _week_key(trading_day)
            if enforce_weekly_cap and weekly_open_counts[week_key] >= WEEKLY_NEW_TRADE_CAP:
                skipped_trades.append(trade)
                return
            if capital_limit is not None and cash < ENTRY_CAPITAL:
                skipped_trades.append(trade)
                return

            key = (trade.strategy, trade.ticker, trade.entry_time)
            open_positions[key] = OpenPosition(trade=trade)
            executed_trades.append(trade)
            cash -= ENTRY_CAPITAL
            if enforce_weekly_cap:
                weekly_open_counts[week_key] += 1
            deployed_now = len(open_positions) * ENTRY_CAPITAL
            if deployed_now > max_deployed:
                max_deployed = deployed_now

        for trade in weekly_candidates:
            maybe_open(trade, enforce_weekly_cap=True, trading_day=current_day)
        for trade in daily_candidates:
            maybe_open(trade, enforce_weekly_cap=False, trading_day=current_day)

        marked_value = 0.0
        for position in open_positions.values():
            marked_value += position.trade.shares * get_close_asof(
                price_cache, position.trade.ticker, current_day
            )

        raw_equity = cash + marked_value
        daily_rows.append(
            {
                "date": current_day,
                "cash": cash,
                "marked_value": marked_value,
                "raw_equity": raw_equity,
                "open_positions": len(open_positions),
                "deployed_capital": len(open_positions) * ENTRY_CAPITAL,
            }
        )

    equity_df = pd.DataFrame(daily_rows).sort_values("date").reset_index(drop=True)
    if capital_limit is None:
        baseline_capital = max(max_deployed, ENTRY_CAPITAL)
        equity_df["equity"] = equity_df["raw_equity"] + baseline_capital
    else:
        equity_df["equity"] = equity_df["raw_equity"]

    return {
        "equity_curve": equity_df,
        "executed_trades": executed_trades,
        "skipped_trades": skipped_trades,
        "max_deployed_capital": max_deployed,
        "baseline_capital": baseline_capital,
        "ending_equity": float(equity_df["equity"].iloc[-1]),
    }


def summarize_trades(trades: list[TradeCandidate]) -> pd.DataFrame:
    rows = []
    grouped: dict[tuple[str, str], list[TradeCandidate]] = defaultdict(list)
    for trade in trades:
        grouped[(trade.strategy, trade.segment)].append(trade)

    for (strategy, segment), bucket in sorted(grouped.items()):
        rows.append(
            {
                "strategy": strategy,
                "segment": segment,
                "trades": len(bucket),
                "avg_return_pct": np.mean([trade.return_pct for trade in bucket]),
                "win_rate_pct": np.mean([trade.return_pct > 0 for trade in bucket]) * 100.0,
                "avg_duration_days": np.mean([trade.duration_days for trade in bucket]),
                "avg_sigma": np.mean([trade.sigma_move for trade in bucket]),
                "total_pnl_inr": np.sum([trade.pnl for trade in bucket]),
            }
        )

    return pd.DataFrame(rows)


def annual_summary(equity_curve: pd.DataFrame) -> pd.DataFrame:
    curve = equity_curve.copy()
    curve["year"] = pd.to_datetime(curve["date"]).dt.year
    rows = []
    for year, group in curve.groupby("year"):
        start_equity = float(group["equity"].iloc[0])
        end_equity = float(group["equity"].iloc[-1])
        rows.append(
            {
                "year": int(year),
                "start_equity": start_equity,
                "end_equity": end_equity,
                "pnl": end_equity - start_equity,
                "return_pct": ((end_equity / start_equity) - 1.0) * 100.0
                if start_equity > 0
                else np.nan,
                "max_deployed": float(group["deployed_capital"].max()),
            }
        )
    return pd.DataFrame(rows)


def format_inr_human(value: float) -> str:
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 10_000_000:
        return f"{sign}INR {abs_value / 10_000_000:.2f} cr ({abs_value / 1_000_000:.2f} mn)"
    if abs_value >= 100_000:
        return f"{sign}INR {abs_value / 100_000:.2f} lakh ({abs_value / 1_000_000:.2f} mn)"
    if abs_value >= 1_000_000:
        return f"{sign}INR {abs_value / 1_000_000:.2f} mn"
    return f"{sign}INR {abs_value:,.2f}"


def _write_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows_\n"
    formatted = df.copy()
    currency_columns = {
        "total_pnl_inr",
        "start_equity",
        "end_equity",
        "pnl",
        "max_deployed",
    }
    percent_columns = {
        "avg_return_pct",
        "win_rate_pct",
        "return_pct",
        "avg_sigma",
    }
    decimal_columns = {
        "avg_duration_days",
    }

    for column in formatted.columns:
        if column in currency_columns:
            formatted[column] = formatted[column].map(lambda value: format_inr_human(float(value)))
        elif column in percent_columns:
            formatted[column] = formatted[column].map(lambda value: f"{float(value):.2f}")
        elif column in decimal_columns:
            formatted[column] = formatted[column].map(lambda value: f"{float(value):.2f}")
    return formatted.to_markdown(index=False) + "\n"


def render_report(
    threshold: float,
    trade_summary: pd.DataFrame,
    scenario_a: dict[str, Any],
    scenario_b: dict[str, Any],
    annual_a: pd.DataFrame,
    annual_b: pd.DataFrame,
    output_dir: Path,
) -> str:
    lines = [
        "# c5 / c6 Portfolio Simulation",
        "",
        "## Setup",
        "- Strategies simulated: `c5 W/W`, `c6 D`, `c6 W`",
        "- Strategy omitted: `c5 D/W`",
        "- Universe: combined `N50 + N150 + N250`, with universe-level breakdowns preserved",
        f"- Entry capital per trade: `{format_inr_human(ENTRY_CAPITAL)}`",
        f"- Cone threshold: `sigma < {threshold}`",
        "- Scenario A: infinite capital, baseline capital set to required max deployed capital for reporting",
        f"- Scenario B: capital capped at `{format_inr_human(LIMITED_CAPITAL)}`",
        "- Scenario B ranking: deeper cone discount adjusted by a holding-horizon proxy to favor return-per-day and turnover",
        f"- Scenario B weekly cap: max `{WEEKLY_NEW_TRADE_CAP}` new `W` trades per week across `c5 W/W` and `c6 W` combined",
        "",
        "## Raw Trade Summary By Strategy And Universe",
        _write_table(trade_summary),
        "## Scenario A",
        f"- Ending equity: `{format_inr_human(scenario_a['ending_equity'])}`",
        f"- Max deployed capital: `{format_inr_human(scenario_a['max_deployed_capital'])}`",
        f"- Executed trades: `{len(scenario_a['executed_trades'])}`",
        "",
        _write_table(annual_a),
        "## Scenario B",
        f"- Starting capital: `{format_inr_human(LIMITED_CAPITAL)}`",
        f"- Ending equity: `{format_inr_human(scenario_b['ending_equity'])}`",
        f"- Executed trades: `{len(scenario_b['executed_trades'])}`",
        f"- Skipped trades: `{len(scenario_b['skipped_trades'])}`",
        "",
        _write_table(annual_b),
        "## Charts",
        f"- [equity_curves.png]({output_dir / 'equity_curves.png'})",
        f"- [annual_returns.png]({output_dir / 'annual_returns.png'})",
        f"- [strategy_pnl.png]({output_dir / 'strategy_pnl.png'})",
        "",
    ]
    return "\n".join(lines)


def save_charts(
    output_dir: Path,
    scenario_a: dict[str, Any],
    scenario_b: dict[str, Any],
    annual_a: pd.DataFrame,
    annual_b: pd.DataFrame,
    trade_summary: pd.DataFrame,
) -> None:
    plt.figure(figsize=(14, 7))
    plt.plot(
        scenario_a["equity_curve"]["date"],
        scenario_a["equity_curve"]["equity"],
        label="Scenario A - Infinite Capital",
    )
    plt.plot(
        scenario_b["equity_curve"]["date"],
        scenario_b["equity_curve"]["equity"],
        label="Scenario B - 400k Capital",
    )
    plt.title("Equity Curves")
    plt.xlabel("Date")
    plt.ylabel("Equity (INR)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "equity_curves.png", dpi=150)
    plt.close()

    years = sorted(set(annual_a["year"]).union(set(annual_b["year"])))
    returns_a = annual_a.set_index("year").reindex(years)["return_pct"].fillna(0.0)
    returns_b = annual_b.set_index("year").reindex(years)["return_pct"].fillna(0.0)
    x = np.arange(len(years))
    width = 0.38
    plt.figure(figsize=(14, 7))
    plt.bar(x - width / 2, returns_a, width=width, label="Scenario A")
    plt.bar(x + width / 2, returns_b, width=width, label="Scenario B")
    plt.xticks(x, years, rotation=45)
    plt.title("Annual Returns")
    plt.ylabel("Return %")
    plt.legend()
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "annual_returns.png", dpi=150)
    plt.close()

    strategy_totals = (
        trade_summary.groupby("strategy")["total_pnl_inr"].sum().sort_values(ascending=False)
    )
    plt.figure(figsize=(10, 6))
    plt.bar(strategy_totals.index, strategy_totals.values)
    plt.title("Total PnL By Strategy")
    plt.ylabel("PnL (INR)")
    plt.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "strategy_pnl.png", dpi=150)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument("--cone-threshold", type=float, default=DEFAULT_CONE_THRESHOLD)
    parser.add_argument("--output-dir", default="results/c5_c6_simulation")
    args = parser.parse_args()

    fetch_data_func = get_fetch_data(refresh=args.refresh_data)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating trade candidates for: {', '.join(ACTIVE_STRATEGIES)}")
    trades, price_cache = load_trade_candidates(fetch_data_func, args.cone_threshold)
    trade_summary = summarize_trades(trades)

    print("Running scenario A...")
    scenario_a = simulate_portfolio(trades, price_cache, capital_limit=None)
    annual_a = annual_summary(scenario_a["equity_curve"])

    print("Running scenario B...")
    scenario_b = simulate_portfolio(trades, price_cache, capital_limit=LIMITED_CAPITAL)
    annual_b = annual_summary(scenario_b["equity_curve"])

    save_charts(output_dir, scenario_a, scenario_b, annual_a, annual_b, trade_summary)
    report = render_report(
        args.cone_threshold,
        trade_summary,
        scenario_a,
        scenario_b,
        annual_a,
        annual_b,
        output_dir,
    )

    (output_dir / "report.md").write_text(report, encoding="utf-8")
    trade_summary.round(4).to_csv(output_dir / "trade_summary.csv", index=False)
    annual_a.round(4).to_csv(output_dir / "annual_scenario_a.csv", index=False)
    annual_b.round(4).to_csv(output_dir / "annual_scenario_b.csv", index=False)

    print(f"Saved simulation report to {output_dir / 'report.md'}")


if __name__ == "__main__":
    main()
