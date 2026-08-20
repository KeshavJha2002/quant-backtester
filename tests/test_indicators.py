from __future__ import annotations

import numpy as np
import pytest

from trading_bot.utility.indicators import (
    compute_st_trend_from_config,
    compute_triple_supertrend,
    ema,
    rma,
    rsi,
    sma,
    true_range,
)


def test_true_range_calculation() -> None:
    high = np.array([10.0, 12.0, 11.0, 15.0])
    low = np.array([8.0, 9.0, 10.0, 12.0])
    close = np.array([9.0, 11.0, 10.5, 14.0])

    tr = true_range(high, low, close)

    # Bar 0: high[0] - low[0] = 2.0
    # Bar 1: max(12-9=3, |12-9|=3, |9-9|=0) = 3.0
    # Bar 2: max(11-10=1, |11-11|=0, |10-11|=1) = 1.0
    # Bar 3: max(15-12=3, |15-10.5|=4.5, |12-10.5|=1.5) = 4.5
    expected = np.array([2.0, 3.0, 1.0, 4.5])
    np.testing.assert_allclose(tr, expected, rtol=1e-10)


def test_true_range_empty_and_single() -> None:
    assert len(true_range(np.array([]), np.array([]), np.array([]))) == 0
    single = true_range(np.array([10.0]), np.array([8.0]), np.array([9.0]))
    assert len(single) == 1
    assert single[0] == 2.0


def test_rma_calculation() -> None:
    series = np.array([10.0, 12.0, 14.0, 16.0, 18.0])
    length = 3

    out = rma(series, length)
    # First 2 should be NaN
    assert np.isnan(out[0])
    assert np.isnan(out[1])
    # Index 2: mean of [10, 12, 14] = 12.0
    assert out[2] == pytest.approx(12.0)
    # Index 3: 12.0 + (1/3)*(16.0 - 12.0) = 12.0 + 1.33333333 = 13.33333333
    assert out[3] == pytest.approx(13.33333333)
    # Index 4: 13.33333333 + (1/3)*(18.0 - 13.33333333) = 14.88888888
    assert out[4] == pytest.approx(14.88888888)


def test_sma_calculation() -> None:
    series = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    length = 3
    out = sma(series, length)

    assert np.isnan(out[0])
    assert np.isnan(out[1])
    assert out[2] == pytest.approx(2.0)
    assert out[3] == pytest.approx(3.0)
    assert out[4] == pytest.approx(4.0)


def test_ema_calculation() -> None:
    series = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
    length = 3

    out = ema(series, length)
    assert np.isnan(out[0])
    assert np.isnan(out[1])
    # Index 2: mean of [10, 11, 12] = 11.0
    assert out[2] == pytest.approx(11.0)
    # Index 3: 0.5 * 13 + 0.5 * 11 = 12.0
    assert out[3] == pytest.approx(12.0)
    # Index 4: 0.5 * 14 + 0.5 * 12 = 13.0
    assert out[4] == pytest.approx(13.0)


def test_rsi_bounds_and_behavior() -> None:
    # All increasing prices should result in high RSI (close to 100)
    increasing = np.array([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0])
    rsi_up = rsi(increasing, length=3)
    valid_up = rsi_up[~np.isnan(rsi_up)]
    assert len(valid_up) > 0
    assert all(val >= 90.0 for val in valid_up[-3:])

    # All decreasing prices should result in low RSI (close to 0)
    decreasing = np.array([20.0, 19.0, 18.0, 17.0, 16.0, 15.0, 14.0, 13.0, 12.0, 11.0, 10.0])
    rsi_down = rsi(decreasing, length=3)
    valid_down = rsi_down[~np.isnan(rsi_down)]
    assert len(valid_down) > 0
    assert all(val <= 10.0 for val in valid_down[-3:])


def test_supertrend_computation() -> None:
    # Construct steady uptrend data
    close = np.linspace(100, 200, 30)
    high = close + 2.0
    low = close - 2.0

    trend = compute_st_trend_from_config(close, high, low, atr_len=5, atr_mult=2.0, smooth_len=1)
    assert len(trend) == 30
    # Uptrend should be bullish (+1) after initial warm up
    assert all(t == 1 for t in trend[10:])

    # Test triple supertrend helper
    t1, t2, t3 = compute_triple_supertrend(close, high, low)
    assert len(t1) == 30
    assert len(t2) == 30
    assert len(t3) == 30
    assert all(t == 1 for t in t1[15:])
    assert all(t == 1 for t in t2[15:])
    assert all(t == 1 for t in t3[15:])
