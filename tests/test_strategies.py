from __future__ import annotations

from pathlib import Path

import pytest

from trading_bot.mtf.supertrend import run_supertrend_mtf_scan
from trading_bot.mtf.tema_macd import run_tema_macd_mtf_scan
from trading_bot.strategy.combination import (
    build_c1,
    build_c2,
    build_c3,
    build_c4,
    build_c5,
    build_c6,
    build_c7,
    c1_tema_macd_mtf,
    c2_trend_supertrend_mtf,
    c3_tema_macd_mtf_projection_cone_d,
    c4_trend_supertrend_mtf_projection_cone_d,
    c5_tema_macd_projection_cone_w,
    c5_tw,
    c6_trend_supertrend_projection_cone_w,
    c6_tw,
    c7_quantum_supertrend_cone_mtf,
)
from trading_bot.strategy.common import StrategyContext
from trading_bot.strategy.registry import run_strategies, run_strategy
from trading_bot.strategy.standalone import (
    build_s1,
    build_s2,
    build_s3,
    s1_tema_macd,
    s2_trend_supertrend,
    s3_projection_cone,
)
from trading_bot.supertrend.strategy import run_supertrend_scans
from trading_bot.tema_macd.strategy import (
    tema_macd_active_bull_screen,
    tema_macd_fresh_bull_screen,
)
from trading_bot.utility import MarketDataStore, config, get_fetch_data

FIXTURE_CACHE = Path(__file__).resolve().parent / "fixtures" / "data_cache"


@pytest.fixture
def fixture_fetcher():
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    return get_fetch_data(store=store)


def test_tema_macd_screens_on_fixture(fixture_fetcher) -> None:
    test_config = {**config, "tema_len": 3, "macd_fast": 3, "macd_slow": 6, "macd_signal": 3}
    active_bulls = tema_macd_active_bull_screen(["SAMPLE.NS"], fixture_fetcher, "D", test_config)
    assert isinstance(active_bulls, list)

    fresh_bulls = tema_macd_fresh_bull_screen(["SAMPLE.NS"], fixture_fetcher, "D", test_config)
    assert isinstance(fresh_bulls, list)


def test_supertrend_scans_on_fixture(fixture_fetcher) -> None:
    bull, recent_5, recent_2 = run_supertrend_scans(
        ["SAMPLE.NS"], fixture_fetcher, "D", mode="pullback"
    )
    assert isinstance(bull["D"], list)
    assert isinstance(recent_5["D"], list)
    assert isinstance(recent_2["D"], list)


def test_mtf_scans_on_fixture(fixture_fetcher) -> None:
    test_config = {**config, "tema_len": 3, "macd_fast": 3, "macd_slow": 6, "macd_signal": 3}
    tema_filtered, _ = run_tema_macd_mtf_scan(
        ["SAMPLE.NS"], fixture_fetcher, test_config, tight=False
    )
    assert isinstance(tema_filtered, list)

    super_filtered, _ = run_supertrend_mtf_scan(["SAMPLE.NS"], fixture_fetcher)
    assert isinstance(super_filtered, list)


def test_strategy_builders_on_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    from trading_bot.strategy import common as strat_common

    mock_universes = [("N50", ["SAMPLE.NS"])]
    monkeypatch.setattr("trading_bot.utility.data_store.default_data_store", store)
    monkeypatch.setattr("trading_bot.utility.default_data_store", store)
    monkeypatch.setattr(strat_common, "UNIVERSES", mock_universes)
    monkeypatch.setattr(s1_tema_macd, "UNIVERSES", mock_universes)
    monkeypatch.setattr(s2_trend_supertrend, "UNIVERSES", mock_universes)
    monkeypatch.setattr(s3_projection_cone, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c1_tema_macd_mtf, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c2_trend_supertrend_mtf, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c3_tema_macd_mtf_projection_cone_d, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c4_trend_supertrend_mtf_projection_cone_d, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c5_tema_macd_projection_cone_w, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c5_tw, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c6_trend_supertrend_projection_cone_w, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c6_tw, "UNIVERSES", mock_universes)
    monkeypatch.setattr(c7_quantum_supertrend_cone_mtf, "UNIVERSES", mock_universes)

    context = StrategyContext()

    # Test standalone builders
    s1 = build_s1(context)
    assert s1.strategy_number == 1
    assert "Standalone Strategy 1" in s1.title

    s2 = build_s2(context)
    assert s2.strategy_number == 2

    s3 = build_s3(context)
    assert s3.strategy_number == 3

    # Test combination builders
    c1 = build_c1(context)
    assert c1.strategy_number == 1

    c2 = build_c2(context)
    assert c2.strategy_number == 2

    c3 = build_c3(context)
    assert c3.strategy_number == 3

    c4 = build_c4(context)
    assert c4.strategy_number == 4

    c5 = build_c5(context)
    assert c5.strategy_number == 5

    c6 = build_c6(context)
    assert c6.strategy_number == 6

    c7 = build_c7(context)
    assert c7.strategy_number == 7

    c5_tw_sec = c5_tw.build_section(context)
    assert "c5_tw" in c5_tw_sec.content

    c6_tw_sec = c6_tw.build_section(context)
    assert "c6_tw" in c6_tw_sec.content


def test_strategy_registry_errors() -> None:
    with pytest.raises(ValueError, match="mode must be 'standalone' or 'combination'"):
        run_strategy(mode="invalid", strategy=1)

    with pytest.raises(ValueError, match="Unknown strategy number"):
        run_strategy(mode="standalone", strategy=99)

    with pytest.raises(ValueError, match="Unknown strategy number"):
        run_strategies(mode="combination", strategies=[99])
