from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.projection_cone import ProjectionConeConfig, analyze_projection_cone
from trading_bot.tema_macd.strategy import _latest_complete_bar_index, _tema_macd_state
from trading_bot.utility import (
    compute_st_trend_from_config,
    config,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
)

UNIVERSE_MAP = {
    "N50": set(nifty50_ns),
    "N150": set(nifty150_ns),
    "N250": set(nifty250_ns),
}


@dataclass(frozen=True)
class StrategyMatch:
    label: str
    mode: str
    strategy_no: int
    timeframe: str
    state: str
    details: str


@dataclass(frozen=True)
class PositionDecision:
    ticker: str
    strategy_no: int
    decision: str
    reason: str
    context: dict[str, Any]


def normalize_ticker(raw_ticker: str) -> str:
    ticker = raw_ticker.strip().upper()
    if not ticker.endswith(".NS"):
        ticker = f"{ticker}.NS"
    return ticker


def detect_universe(ticker: str) -> str:
    memberships = [name for name, tickers in UNIVERSE_MAP.items() if ticker in tickers]
    return ", ".join(memberships) if memberships else "Custom"


def get_cached_fetcher():
    return get_fetch_data(refresh=False)


def get_complete_data(fetch_data_func, ticker: str, freq: str) -> tuple[pd.DataFrame, int]:
    data = fetch_data_func(ticker, type=freq).reset_index(drop=True)
    idx = _latest_complete_bar_index(np.asarray(data["time"].values), freq)
    if idx is None or idx <= 0:
        raise ValueError(f"No complete {freq} bar available for {ticker}")
    return data.iloc[: idx + 1].reset_index(drop=True), idx


def tema_state_snapshot(fetch_data_func, ticker: str, freq: str) -> dict[str, Any]:
    data, idx = get_complete_data(fetch_data_func, ticker, freq)
    close = np.asarray(data["close"].values, dtype=float).ravel()

    if len(close) < max(config["tema_len"], config["macd_slow"]) + 5:
        raise ValueError(f"Not enough {freq} data for {ticker}")

    tema, macd, signal, state_before_bar, state_after_bar = _tema_macd_state(close, config)
    if np.isnan(tema[idx]) or np.isnan(macd[idx]) or np.isnan(signal[idx]):
        raise ValueError(f"Indicator values unavailable for {ticker} {freq}")

    fresh_buy = bool(
        tema[idx] >= tema[idx - 1] and not state_before_bar[idx] and macd[idx] >= signal[idx]
    )
    fresh_sell = bool(
        tema[idx] < tema[idx - 1] and state_before_bar[idx] and macd[idx] < signal[idx]
    )
    active_bull = bool(state_after_bar[idx])

    return {
        "bar_time": str(pd.to_datetime(data["time"].iloc[idx])),
        "fresh_buy": fresh_buy,
        "fresh_sell": fresh_sell,
        "active_bull": active_bull,
        "close": float(close[idx]),
        "tema": float(tema[idx]),
        "macd": float(macd[idx]),
        "signal": float(signal[idx]),
    }


def _supertrend_or_snapshot(data: pd.DataFrame) -> dict[str, Any]:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()

    trend1 = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend2 = compute_st_trend_from_config(close, high, low, 14, 3.0, 2)
    trend3 = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)
    idx = len(close) - 1
    fresh_buy = bool(
        (trend1[idx - 1] == -1 and trend1[idx] == 1)
        or (trend2[idx - 1] == -1 and trend2[idx] == 1)
        or (trend3[idx - 1] == -1 and trend3[idx] == 1)
    )
    bullish = bool(trend1[idx] == 1 or trend2[idx] == 1 or trend3[idx] == 1)

    return {
        "fresh_buy": fresh_buy,
        "bullish": bullish,
        "close": float(close[idx]),
    }


def _supertrend_pullback_snapshot(data: pd.DataFrame, grace_lb: int = 2) -> dict[str, Any]:
    close = np.asarray(data["close"].values, float).ravel()
    high = np.asarray(data["high"].values, float).ravel()
    low = np.asarray(data["low"].values, float).ravel()

    trend_fast = compute_st_trend_from_config(close, high, low, 10, 3.0, 1)
    trend_slow = compute_st_trend_from_config(close, high, low, 14, 3.5, 3)
    idx = len(close) - 1

    fresh_buy = bool(trend_fast[idx - 1] == -1 and trend_fast[idx] == 1 and trend_slow[idx] == 1)
    slow_bull = bool(trend_slow[idx] == 1)
    fast_bull = bool(trend_fast[idx] == 1)

    hold = True
    reason = "daily regime intact"
    if trend_slow[idx] == -1:
        hold = False
        reason = "slow supertrend turned bearish"
    elif trend_fast[idx] == -1:
        recovered = False
        for lookback_idx in range(max(1, len(close) - grace_lb), len(close)):
            if trend_fast[lookback_idx] == 1:
                recovered = True
                break
        if not recovered:
            hold = False
            reason = "fast supertrend stayed bearish through grace window"

    return {
        "fresh_buy": fresh_buy,
        "slow_bull": slow_bull,
        "fast_bull": fast_bull,
        "hold": hold,
        "reason": reason,
        "close": float(close[idx]),
    }


def supertrend_state_snapshot(fetch_data_func, ticker: str, freq: str) -> dict[str, Any]:
    data, idx = get_complete_data(fetch_data_func, ticker, freq)
    if freq == "D":
        result = _supertrend_pullback_snapshot(data)
    else:
        result = _supertrend_or_snapshot(data)
        result["hold"] = bool(result["bullish"])
        result["reason"] = "weekly regime bullish" if result["bullish"] else "weekly regime bearish"

    result["bar_time"] = str(pd.to_datetime(data["time"].iloc[idx]))
    return result


def cone_snapshot(fetch_data_func, ticker: str, freq: str) -> dict[str, Any]:
    cone_config = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)

    def complete_fetcher(request_ticker: str, *, type: str):
        data, _ = get_complete_data(fetch_data_func, request_ticker, type)
        return data

    result = analyze_projection_cone(
        ticker,
        fetch_data_func=complete_fetcher,
        freq=freq,
        config=cone_config,
    )
    return {
        "bar_time": result["as_of"],
        "price": float(result["current_price"]),
        "sigma_move": float(result["zone"]["sigma_move"]),
        "sigma_bucket": result["zone"]["name"],
        "anchor_type": result["anchor"]["type"],
    }


def build_ticker_strategy_snapshot(ticker: str) -> dict[str, Any]:
    normalized_ticker = normalize_ticker(ticker)
    fetcher = get_cached_fetcher()

    tema_d = tema_state_snapshot(fetcher, normalized_ticker, "D")
    tema_w = tema_state_snapshot(fetcher, normalized_ticker, "W")
    super_d = supertrend_state_snapshot(fetcher, normalized_ticker, "D")
    super_w = supertrend_state_snapshot(fetcher, normalized_ticker, "W")
    cone_d = cone_snapshot(fetcher, normalized_ticker, "D")
    cone_w = cone_snapshot(fetcher, normalized_ticker, "W")

    matches: list[StrategyMatch] = []

    if tema_d["active_bull"]:
        matches.append(
            StrategyMatch(
                label="Standalone 1 (TEMA MACD D)",
                mode="standalone",
                strategy_no=1,
                timeframe="D",
                state="buy",
                details=f"last D signal still buy as of {tema_d['bar_time']}",
            )
        )
    if tema_w["active_bull"]:
        matches.append(
            StrategyMatch(
                label="Standalone 1 (TEMA MACD W)",
                mode="standalone",
                strategy_no=1,
                timeframe="W",
                state="buy",
                details=f"last W signal still buy as of {tema_w['bar_time']}",
            )
        )
    if super_d["hold"]:
        matches.append(
            StrategyMatch(
                label="Standalone 2 (Trend Supertrend D)",
                mode="standalone",
                strategy_no=2,
                timeframe="D",
                state="buy",
                details=f"D trend regime active as of {super_d['bar_time']}",
            )
        )
    if super_w["hold"]:
        matches.append(
            StrategyMatch(
                label="Standalone 2 (Trend Supertrend W)",
                mode="standalone",
                strategy_no=2,
                timeframe="W",
                state="buy",
                details=f"W trend regime active as of {super_w['bar_time']}",
            )
        )
    if tema_d["active_bull"] and tema_w["active_bull"]:
        matches.append(
            StrategyMatch(
                label="Combination 1 (TEMA MACD D in W)",
                mode="combination",
                strategy_no=1,
                timeframe="D/W",
                state="buy",
                details="daily TEMA buy state inside weekly bullish state",
            )
        )
    if super_d["hold"] and super_w["hold"]:
        matches.append(
            StrategyMatch(
                label="Combination 2 (Trend Supertrend D in W)",
                mode="combination",
                strategy_no=2,
                timeframe="D/W",
                state="buy",
                details="daily Supertrend hold state inside weekly bullish regime",
            )
        )
    if tema_d["active_bull"] and tema_w["active_bull"] and cone_d["sigma_move"] < 0:
        matches.append(
            StrategyMatch(
                label="Combination 3 (TEMA MACD D in W + Projection Cone D)",
                mode="combination",
                strategy_no=3,
                timeframe="D/W",
                state="buy",
                details=f"daily/weekly TEMA buy state with D cone sigma {cone_d['sigma_move']:.2f}",
            )
        )
    if super_d["hold"] and super_w["hold"] and cone_d["sigma_move"] < 0:
        matches.append(
            StrategyMatch(
                label="Combination 4 (Trend Supertrend D in W + Projection Cone D)",
                mode="combination",
                strategy_no=4,
                timeframe="D/W",
                state="buy",
                details=f"daily/weekly Supertrend buy state with D cone sigma {cone_d['sigma_move']:.2f}",
            )
        )
    if tema_w["active_bull"] and cone_w["sigma_move"] < 0:
        matches.append(
            StrategyMatch(
                label="Combination 5 (TEMA MACD W + Projection Cone W)",
                mode="combination",
                strategy_no=5,
                timeframe="W",
                state="buy",
                details=f"weekly TEMA buy state with W cone sigma {cone_w['sigma_move']:.2f}",
            )
        )
    if super_w["hold"] and cone_w["sigma_move"] < 0:
        matches.append(
            StrategyMatch(
                label="Combination 6 (Trend Supertrend W + Projection Cone W)",
                mode="combination",
                strategy_no=6,
                timeframe="W",
                state="buy",
                details=f"weekly Supertrend buy state with W cone sigma {cone_w['sigma_move']:.2f}",
            )
        )

    return {
        "ticker": normalized_ticker,
        "universe": detect_universe(normalized_ticker),
        "tema_d": tema_d,
        "tema_w": tema_w,
        "supertrend_d": super_d,
        "supertrend_w": super_w,
        "cone_d": cone_d,
        "cone_w": cone_w,
        "matches": matches,
    }


def evaluate_combination_position(ticker: str, strategy_no: int) -> PositionDecision:
    normalized_ticker = normalize_ticker(ticker)
    fetcher = get_cached_fetcher()

    tema_d = tema_state_snapshot(fetcher, normalized_ticker, "D")
    tema_w = tema_state_snapshot(fetcher, normalized_ticker, "W")
    super_d = supertrend_state_snapshot(fetcher, normalized_ticker, "D")
    super_w = supertrend_state_snapshot(fetcher, normalized_ticker, "W")
    cone_d = cone_snapshot(fetcher, normalized_ticker, "D")
    cone_w = cone_snapshot(fetcher, normalized_ticker, "W")

    context = {
        "universe": detect_universe(normalized_ticker),
        "tema_d_active": tema_d["active_bull"],
        "tema_w_active": tema_w["active_bull"],
        "supertrend_d_hold": super_d["hold"],
        "supertrend_w_hold": super_w["hold"],
        "cone_d_sigma": cone_d["sigma_move"],
        "cone_w_sigma": cone_w["sigma_move"],
    }

    if strategy_no == 1:
        hold = tema_d["active_bull"] and tema_w["active_bull"]
        reason = (
            "daily and weekly TEMA states still bullish"
            if hold
            else "daily or weekly TEMA state has broken"
        )
    elif strategy_no == 2:
        hold = super_d["hold"] and super_w["hold"]
        reason = (
            "daily and weekly Supertrend regimes still bullish"
            if hold
            else "daily or weekly Supertrend regime has broken"
        )
    elif strategy_no == 3:
        hold = tema_d["active_bull"] and tema_w["active_bull"]
        reason = (
            "trend leg remains valid; D cone was treated as entry filter only"
            if hold
            else "daily or weekly TEMA state has broken"
        )
    elif strategy_no == 4:
        hold = super_d["hold"] and super_w["hold"]
        reason = (
            "trend leg remains valid; D cone was treated as entry filter only"
            if hold
            else "daily or weekly Supertrend regime has broken"
        )
    elif strategy_no == 5:
        hold = tema_w["active_bull"]
        reason = (
            "weekly TEMA state still bullish; W cone was treated as entry filter only"
            if hold
            else "weekly TEMA state has broken"
        )
    elif strategy_no == 6:
        hold = super_w["hold"]
        reason = (
            "weekly Supertrend regime still bullish; W cone was treated as entry filter only"
            if hold
            else "weekly Supertrend regime has broken"
        )
    else:
        raise ValueError("strategy_no must be between 1 and 6 for combination strategies")

    return PositionDecision(
        ticker=normalized_ticker,
        strategy_no=strategy_no,
        decision="hold" if hold else "sell",
        reason=reason,
        context=context,
    )


def format_snapshot_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        f"# Strategy Snapshot: {snapshot['ticker']}",
        f"- Universe: `{snapshot['universe']}`",
        "",
        "## Matches",
        "| Mode | Strategy | Timeframe | State | Details |",
        "|---|---|---|---|---|",
    ]
    matches: list[StrategyMatch] = snapshot["matches"]
    if matches:
        for match in matches:
            lines.append(
                f"| {match.mode} | {match.strategy_no} | {match.timeframe} | {match.state} | {match.details} |"
            )
    else:
        lines.append("| - | - | - | - | No current buy-state match across the tracked strategies |")

    lines.extend(
        [
            "",
            "## Context",
            "| Signal | Value |",
            "|---|---|",
            f"| TEMA D active bull | `{snapshot['tema_d']['active_bull']}` |",
            f"| TEMA W active bull | `{snapshot['tema_w']['active_bull']}` |",
            f"| Supertrend D hold | `{snapshot['supertrend_d']['hold']}` |",
            f"| Supertrend W hold | `{snapshot['supertrend_w']['hold']}` |",
            f"| D cone sigma | `{snapshot['cone_d']['sigma_move']:.2f}` |",
            f"| W cone sigma | `{snapshot['cone_w']['sigma_move']:.2f}` |",
        ]
    )
    return "\n".join(lines)


def format_position_decisions_markdown(decisions: list[PositionDecision]) -> str:
    lines = [
        "# Combination Position Decisions",
        "",
        "| Ticker | Strategy | Decision | Reason | D Cone Sigma | W Cone Sigma |",
        "|---|---:|---|---|---:|---:|",
    ]
    for decision in decisions:
        lines.append(
            f"| {decision.ticker} | {decision.strategy_no} | {decision.decision} | {decision.reason} | "
            f"{decision.context['cone_d_sigma']:.2f} | {decision.context['cone_w_sigma']:.2f} |"
        )
    if not decisions:
        lines.append("| - | - | - | - | - | - |")
    return "\n".join(lines)


def parse_pairs(raw_pairs: list[str]) -> list[tuple[str, int]]:
    parsed: list[tuple[str, int]] = []
    for raw_pair in raw_pairs:
        ticker_token, strategy_token = [value.strip() for value in raw_pair.split(":", 1)]
        parsed.append((normalize_ticker(ticker_token), int(strategy_token)))
    return parsed


def parse_pairs_json(raw_json: str) -> list[tuple[str, int]]:
    payload = json.loads(raw_json)
    parsed: list[tuple[str, int]] = []
    for item in payload:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("Each pair in JSON must be [ticker, strategy_no]")
        parsed.append((normalize_ticker(str(item[0])), int(item[1])))
    return parsed
