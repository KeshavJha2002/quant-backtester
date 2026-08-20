from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from trading_bot.projection_cone import (
    ProjectionConeConfig,
    analyze_projection_cone,
    calculate_annual_volatility,
    calculate_cone_price,
    calculate_percent_rank,
    calculate_sigma_move,
    find_last_pivot,
    format_projection_cone_report,
    get_sigma_bucket,
    get_vol_regime_from_percentile,
    get_zone_from_sigma,
    resolve_bars_per_year,
)
from trading_bot.utility import MarketDataStore, get_fetch_data

FIXTURE_CACHE = Path(__file__).resolve().parent / "fixtures" / "data_cache"


def test_resolve_bars_per_year() -> None:
    assert resolve_bars_per_year("D", None) == 252
    assert resolve_bars_per_year("W", None) == 52
    assert resolve_bars_per_year("D", 300) == 300


def test_calculate_annual_volatility() -> None:
    # 5 close prices
    close = np.array([100.0, 102.0, 101.0, 103.0, 105.0])
    vol = calculate_annual_volatility(close, vol_length=3, bars_per_year=252)
    assert len(vol) == 5
    assert np.isnan(vol[0])
    assert np.isnan(vol[1])
    assert not np.isnan(vol[3])
    assert vol[3] > 0


def test_calculate_percent_rank() -> None:
    values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
    # 50.0 is the max out of 5 -> 100%
    assert calculate_percent_rank(values, 5) == pytest.approx(100.0)
    # 10.0 would be 20%
    values_min = np.array([50.0, 40.0, 30.0, 20.0, 10.0])
    assert calculate_percent_rank(values_min, 5) == pytest.approx(20.0)


def test_find_last_pivot() -> None:
    # Create high/low with a distinct pivot high at index 3
    high = np.array([10.0, 12.0, 14.0, 20.0, 13.0, 11.0, 9.0])
    low = np.array([8.0, 9.0, 10.0, 12.0, 10.0, 8.0, 7.0])

    pivot_high = find_last_pivot(high, low, pivot_len=2, lock_to_bull=False)
    assert pivot_high == 3

    # Create low with distinct pivot low at index 3
    high_l = np.array([20.0, 18.0, 16.0, 15.0, 17.0, 19.0, 21.0])
    low_l = np.array([18.0, 15.0, 12.0, 5.0, 11.0, 14.0, 16.0])
    pivot_low = find_last_pivot(high_l, low_l, pivot_len=2, lock_to_bull=True)
    assert pivot_low == 3


def test_calculate_cone_price() -> None:
    base = 100.0
    vol = 0.20
    bars = 252
    price_upper_1s = calculate_cone_price(base, vol, bars, 1.0, 1, 252)
    price_lower_1s = calculate_cone_price(base, vol, bars, 1.0, -1, 252)

    assert price_upper_1s == pytest.approx(base * np.exp(0.20))
    assert price_lower_1s == pytest.approx(base * np.exp(-0.20))


def test_calculate_sigma_move() -> None:
    # Current = Anchor -> sigma = 0
    assert calculate_sigma_move(100.0, 100.0, 0.20, 10, 252) == pytest.approx(0.0)
    # Higher price -> positive sigma
    assert calculate_sigma_move(110.0, 100.0, 0.20, 10, 252) > 0
    # Lower price -> negative sigma
    assert calculate_sigma_move(90.0, 100.0, 0.20, 10, 252) < 0


def test_get_zone_and_bucket() -> None:
    zone, color = get_zone_from_sigma(0.5)
    assert zone == "Inside 1σ"
    zone3, _ = get_zone_from_sigma(3.5)
    assert zone3 == "Beyond 3σ"

    bucket_u = get_sigma_bucket(-1.5, unicode_symbol=True)
    assert bucket_u == "-2σ to -1σ"
    bucket_a = get_sigma_bucket(-1.5, unicode_symbol=False)
    assert bucket_a == "-2sigma to -1sigma"

    regime, _ = get_vol_regime_from_percentile(75.0)
    assert regime == "HIGH"
    regime_low, _ = get_vol_regime_from_percentile(15.0)
    assert regime_low == "LOW"


def test_analyze_projection_cone_with_fixture() -> None:
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    fetcher = get_fetch_data(store=store)
    config = ProjectionConeConfig(vol_length=3, pivot_len=2, proj_bars=10)

    result = analyze_projection_cone("SAMPLE.NS", fetch_data_func=fetcher, freq="D", config=config)

    assert result["ticker"] == "SAMPLE.NS"
    assert result["timeframe"] == "D"
    assert "current_price" in result
    assert "zone" in result
    assert "volatility" in result
    assert "projection" in result

    report = format_projection_cone_report(result)
    assert "SAMPLE.NS D" in report
    assert "Zone:" in report
