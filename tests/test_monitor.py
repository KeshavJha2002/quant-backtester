from __future__ import annotations

from pathlib import Path

import pytest

from trading_bot.monitor.common import (
    PositionDecision,
    build_ticker_strategy_snapshot,
    detect_universe,
    evaluate_combination_position,
    format_position_decisions_markdown,
    format_snapshot_markdown,
    normalize_ticker,
    parse_pairs,
    parse_pairs_json,
)
from trading_bot.utility import MarketDataStore

FIXTURE_CACHE = Path(__file__).resolve().parent / "fixtures" / "data_cache"


def test_normalize_ticker() -> None:
    assert normalize_ticker("infy") == "INFY.NS"
    assert normalize_ticker("TCS.NS") == "TCS.NS"
    assert normalize_ticker("  reliance.ns  ") == "RELIANCE.NS"


def test_detect_universe() -> None:
    assert "N50" in detect_universe("RELIANCE.NS")
    assert "N150" in detect_universe("BSE.NS")
    assert "N250" in detect_universe("ZENSARTECH.NS")
    assert detect_universe("UNKNOWN_STOCK.NS") == "Custom"


def test_parse_pairs() -> None:
    pairs = parse_pairs(["INFY:1", "TCS.NS:5", "RELIANCE:6"])
    assert pairs == [("INFY.NS", 1), ("TCS.NS", 5), ("RELIANCE.NS", 6)]


def test_parse_pairs_json() -> None:
    raw_json = '[["INFY", 1], ["TCS.NS", 5]]'
    pairs = parse_pairs_json(raw_json)
    assert pairs == [("INFY.NS", 1), ("TCS.NS", 5)]

    with pytest.raises(ValueError, match="must be"):
        parse_pairs_json('["INVALID"]')


def test_format_position_decisions_markdown() -> None:
    decisions = [
        PositionDecision(
            ticker="INFY.NS",
            strategy_no=5,
            decision="hold",
            reason="weekly TEMA state still bullish",
            context={"cone_d_sigma": -0.5, "cone_w_sigma": -1.2},
        )
    ]
    md = format_position_decisions_markdown(decisions)
    assert "INFY.NS" in md
    assert "hold" in md
    assert "weekly TEMA state still bullish" in md


def test_format_empty_position_decisions() -> None:
    md = format_position_decisions_markdown([])
    assert "| - | - | - | - | - | - |" in md


def test_monitor_snapshot_and_evaluation_with_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    from trading_bot.monitor import common as monitor_common

    monkeypatch.setattr(monitor_common, "get_cached_fetcher", lambda: store.fetch_data)

    snapshot = build_ticker_strategy_snapshot("SAMPLE.NS")
    assert snapshot["ticker"] == "SAMPLE.NS"
    assert "tema_d" in snapshot
    assert "supertrend_d" in snapshot

    md_report = format_snapshot_markdown(snapshot)
    assert "Strategy Snapshot: SAMPLE.NS" in md_report

    # Test combination position evaluations 1 through 6
    for strat_no in range(1, 7):
        decision = evaluate_combination_position("SAMPLE.NS", strat_no)
        assert decision.ticker == "SAMPLE.NS"
        assert decision.decision in {"hold", "sell"}
        assert len(decision.reason) > 0

    with pytest.raises(ValueError, match="strategy_no must be between 1 and 6"):
        evaluate_combination_position("SAMPLE.NS", 99)
