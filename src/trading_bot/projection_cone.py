from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from trading_bot.utility import fetch_data

C_TEAL = "#00d4aa"
C_VIOLET = "#a855f7"
C_AMBER = "#f59e0b"
C_RED = "#ef4444"


@dataclass(slots=True)
class ProjectionConeConfig:
    vol_length: int = 20
    proj_bars: int = 80
    bars_per_year: int | None = None
    lock_mode: bool = True
    pivot_len: int = 10
    lock_to_bull: bool = False


def resolve_bars_per_year(freq: str, bars_per_year: int | None) -> int:
    """Resolve the number of trading bars per year for a given timeframe frequency."""
    if bars_per_year is not None:
        return bars_per_year
    return 252 if freq == "D" else 52


def calculate_annual_volatility(
    close: np.ndarray, vol_length: int, bars_per_year: int
) -> np.ndarray:
    """Calculate rolling annualized log-return volatility."""
    close = np.asarray(close, dtype=float).ravel()
    n = len(close)
    if n < 2:
        return np.full(n, np.nan, dtype=float)

    log_return = np.full(n, np.nan, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        log_return[1:] = np.log(close[1:] / close[:-1])

    raw_vol = pd.Series(log_return).rolling(vol_length).std(ddof=0).to_numpy()
    return raw_vol * np.sqrt(bars_per_year)


def calculate_percent_rank(values: np.ndarray, lookback: int) -> float:
    """Calculate percentile rank of the latest valid value within the lookback window."""
    valid = values[~np.isnan(values)]
    if len(valid) == 0:
        return float("nan")
    window = valid[-lookback:]
    current = window[-1]
    return float(np.sum(window <= current) / len(window) * 100.0)


def find_last_pivot(
    high: np.ndarray, low: np.ndarray, pivot_len: int, lock_to_bull: bool
) -> int | None:
    """Find the most recent swing pivot high or pivot low index."""
    source = low if lock_to_bull else high
    comparator = np.min if lock_to_bull else np.max
    pivot_index: int | None = None

    for idx in range(pivot_len, len(source) - pivot_len):
        window = source[idx - pivot_len : idx + pivot_len + 1]
        pivot_value = source[idx]
        if np.isnan(window).any() or np.isnan(pivot_value):
            continue
        if pivot_value == comparator(window):
            pivot_index = idx

    return pivot_index


def calculate_cone_price(
    base_price: float,
    vol: float,
    bars_forward: int,
    sigma_multiplier: float,
    direction: int,
    bars_per_year: int,
) -> float:
    """Calculate boundary price at forward horizon for given sigma multiplier and direction (+1/-1)."""
    drift = direction * sigma_multiplier * vol * np.sqrt(float(bars_forward) / float(bars_per_year))
    return float(base_price * np.exp(drift))


def calculate_sigma_move(
    current_price: float,
    anchor_price: float,
    current_vol: float,
    bars_since_anchor: int,
    bars_per_year: int,
) -> float:
    """Calculate the normalized standard deviation (sigma) move from anchor to current price."""
    t_now = max(bars_since_anchor, 1)
    return float(
        np.log(current_price / anchor_price)
        / (current_vol * np.sqrt(float(t_now) / float(bars_per_year)))
    )


def get_zone_from_sigma(sigma_move: float) -> tuple[str, str]:
    """Map sigma move to zone label and color."""
    sigma_abs = abs(sigma_move)
    if sigma_abs <= 1.0:
        return "Inside 1σ", C_TEAL
    if sigma_abs <= 2.0:
        return "Inside 2σ", C_VIOLET
    if sigma_abs <= 3.0:
        return "Inside 3σ", C_AMBER
    return "Beyond 3σ", C_RED


def get_vol_regime_from_percentile(vol_percentile: float) -> tuple[str, str]:
    """Map volatility percentile to regime label and color."""
    if vol_percentile >= 60:
        return "HIGH", C_AMBER
    if vol_percentile >= 30:
        return "NORMAL", C_VIOLET
    return "LOW", C_TEAL


def get_sigma_bucket(sigma_move: float, *, unicode_symbol: bool = True) -> str:
    """Categorize sigma move into standard discrete bucket interval."""
    sym = "σ" if unicode_symbol else "sigma"
    if sigma_move < -3.0:
        return f"< -3{sym}"
    if sigma_move < -2.0:
        return f"-3{sym} to -2{sym}"
    if sigma_move < -1.0:
        return f"-2{sym} to -1{sym}"
    if sigma_move < 0.0:
        return f"-1{sym} to 0{sym}"
    if sigma_move < 1.0:
        return f"0{sym} to +1{sym}"
    if sigma_move < 2.0:
        return f"+1{sym} to +2{sym}"
    if sigma_move < 3.0:
        return f"+2{sym} to +3{sym}"
    return f"> +3{sym}"


def compute_series_entry_sigmas(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    freq: str = "D",
    cone_config: ProjectionConeConfig | None = None,
) -> np.ndarray:
    """Precompute entry sigma moves for all bars in a series at high performance."""
    cone_config = cone_config or ProjectionConeConfig()
    n = len(close)
    sigmas = np.full(n, np.nan)
    pivot_len = cone_config.pivot_len
    lock_to_bull = cone_config.lock_to_bull

    if n < max(cone_config.vol_length + 1, (2 * pivot_len) + 1):
        return sigmas

    bars_per_year = resolve_bars_per_year(freq, cone_config.bars_per_year)
    annual_vol = calculate_annual_volatility(close, cone_config.vol_length, bars_per_year)

    last_pivot_idx: int | None = None
    last_pivot_price: float | None = None

    for i in range(2 * pivot_len, n):
        p_cand = i - pivot_len
        if lock_to_bull:
            window_low = low[p_cand - pivot_len : p_cand + pivot_len + 1]
            if len(window_low) == 2 * pivot_len + 1 and low[p_cand] == np.min(window_low):
                last_pivot_idx = p_cand
                last_pivot_price = float(low[p_cand])
        else:
            window_high = high[p_cand - pivot_len : p_cand + pivot_len + 1]
            if len(window_high) == 2 * pivot_len + 1 and high[p_cand] == np.max(window_high):
                last_pivot_idx = p_cand
                last_pivot_price = float(high[p_cand])

        current_vol = float(annual_vol[i])
        if np.isnan(current_vol) or current_vol <= 0:
            continue

        if cone_config.lock_mode and last_pivot_idx is not None:
            anchor_idx = last_pivot_idx
            anchor_price = last_pivot_price
        else:
            anchor_idx = i
            anchor_price = float(close[i])

        bars_since_anchor = max(i - anchor_idx, 1)
        sigmas[i] = calculate_sigma_move(
            current_price=float(close[i]),
            anchor_price=anchor_price,
            current_vol=current_vol,
            bars_since_anchor=bars_since_anchor,
            bars_per_year=bars_per_year,
        )

    return sigmas


def calculate_entry_sigma(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    idx: int,
    freq: str,
    cone_config: ProjectionConeConfig,
) -> float | None:
    """Calculate the entry sigma move for a bar at index idx."""
    bars_per_year = resolve_bars_per_year(freq, cone_config.bars_per_year)
    annual_vol = calculate_annual_volatility(close[: idx + 1], cone_config.vol_length, bars_per_year)
    current_vol = float(annual_vol[-1])
    if np.isnan(current_vol) or current_vol <= 0:
        return None

    anchor_idx = idx
    anchor_price = float(close[idx])

    if cone_config.lock_mode:
        pivot_idx = find_last_pivot(
            high[: idx + 1],
            low[: idx + 1],
            cone_config.pivot_len,
            cone_config.lock_to_bull,
        )
        if pivot_idx is not None and not np.isnan(annual_vol[pivot_idx]):
            anchor_idx = pivot_idx
            anchor_price = float(low[pivot_idx] if cone_config.lock_to_bull else high[pivot_idx])

    bars_since_anchor = max(idx - anchor_idx, 1)
    return calculate_sigma_move(
        current_price=float(close[idx]),
        anchor_price=anchor_price,
        current_vol=current_vol,
        bars_since_anchor=bars_since_anchor,
        bars_per_year=bars_per_year,
    )


def analyze_projection_cone(
    ticker: str,
    fetch_data_func: Callable[..., pd.DataFrame] = fetch_data,
    freq: str = "D",
    config: ProjectionConeConfig | None = None,
) -> dict[str, Any]:
    """Perform full projection-cone volatility, anchor, boundary and regime analysis on a ticker."""
    config = config or ProjectionConeConfig()
    bars_per_year = resolve_bars_per_year(freq, config.bars_per_year)

    data = fetch_data_func(ticker, type=freq).reset_index(drop=True)
    close = np.asarray(data["close"].values, dtype=float).ravel()
    high = np.asarray(data["high"].values, dtype=float).ravel()
    low = np.asarray(data["low"].values, dtype=float).ravel()

    min_bars = max(config.vol_length + 1, (2 * config.pivot_len) + 1)
    if len(close) < min_bars:
        raise ValueError(
            f"Not enough data for {ticker}. Need at least {min_bars} bars, got {len(close)}."
        )

    annual_vol = calculate_annual_volatility(close, config.vol_length, bars_per_year)
    last_idx = len(close) - 1
    current_price = float(close[last_idx])
    current_vol = float(annual_vol[last_idx])

    if np.isnan(current_vol) or current_vol <= 0:
        raise ValueError(f"Annualized volatility is unavailable for {ticker} on {freq}.")

    anchor_idx = last_idx
    anchor_type = "live_close"
    anchor_price = current_price
    anchor_vol = current_vol

    if config.lock_mode:
        pivot_idx = find_last_pivot(high, low, config.pivot_len, config.lock_to_bull)
        if pivot_idx is not None and not np.isnan(annual_vol[pivot_idx]):
            anchor_idx = pivot_idx
            anchor_type = "pivot_low" if config.lock_to_bull else "pivot_high"
            anchor_price = float(low[pivot_idx] if config.lock_to_bull else high[pivot_idx])
            anchor_vol = float(annual_vol[pivot_idx])

    t_now = max(last_idx - anchor_idx, 1)
    sigma_move = calculate_sigma_move(
        current_price=current_price,
        anchor_price=anchor_price,
        current_vol=current_vol,
        bars_since_anchor=t_now,
        bars_per_year=bars_per_year,
    )

    vol_percentile = calculate_percent_rank(annual_vol, 252)
    vol_regime, vol_regime_color = get_vol_regime_from_percentile(vol_percentile)
    price_zone, price_zone_color = get_zone_from_sigma(sigma_move)

    upper_25 = calculate_cone_price(anchor_price, anchor_vol, t_now, 2.5, 1, bars_per_year)
    lower_25 = calculate_cone_price(anchor_price, anchor_vol, t_now, 2.5, -1, bars_per_year)

    current_boundaries = {
        "1sigma_upper": calculate_cone_price(anchor_price, anchor_vol, t_now, 1.0, 1, bars_per_year),
        "1sigma_lower": calculate_cone_price(anchor_price, anchor_vol, t_now, 1.0, -1, bars_per_year),
        "2sigma_upper": calculate_cone_price(anchor_price, anchor_vol, t_now, 2.0, 1, bars_per_year),
        "2sigma_lower": calculate_cone_price(anchor_price, anchor_vol, t_now, 2.0, -1, bars_per_year),
        "3sigma_upper": calculate_cone_price(anchor_price, anchor_vol, t_now, 3.0, 1, bars_per_year),
        "3sigma_lower": calculate_cone_price(anchor_price, anchor_vol, t_now, 3.0, -1, bars_per_year),
    }

    projected_boundaries = {
        "1sigma_upper": calculate_cone_price(
            anchor_price, anchor_vol, config.proj_bars, 1.0, 1, bars_per_year
        ),
        "1sigma_lower": calculate_cone_price(
            anchor_price, anchor_vol, config.proj_bars, 1.0, -1, bars_per_year
        ),
        "2sigma_upper": calculate_cone_price(
            anchor_price, anchor_vol, config.proj_bars, 2.0, 1, bars_per_year
        ),
        "2sigma_lower": calculate_cone_price(
            anchor_price, anchor_vol, config.proj_bars, 2.0, -1, bars_per_year
        ),
        "3sigma_upper": calculate_cone_price(
            anchor_price, anchor_vol, config.proj_bars, 3.0, 1, bars_per_year
        ),
        "3sigma_lower": calculate_cone_price(
            anchor_price, anchor_vol, config.proj_bars, 3.0, -1, bars_per_year
        ),
    }

    projected_moves_pct = {
        "1sigma": (projected_boundaries["1sigma_upper"] - anchor_price) / anchor_price * 100.0,
        "2sigma": (projected_boundaries["2sigma_upper"] - anchor_price) / anchor_price * 100.0,
        "3sigma": (projected_boundaries["3sigma_upper"] - anchor_price) / anchor_price * 100.0,
    }

    if current_price > upper_25:
        stretch_state = "extended_above_2.5sigma"
    elif current_price < lower_25:
        stretch_state = "extended_below_2.5sigma"
    else:
        stretch_state = "inside_2.5sigma_envelope"

    position_in_25 = (
        (current_price - lower_25) / (upper_25 - lower_25) if upper_25 > lower_25 else np.nan
    )

    result = {
        "ticker": ticker,
        "timeframe": freq,
        "as_of": str(data.loc[last_idx, "time"]),
        "current_price": current_price,
        "anchor": {
            "type": anchor_type,
            "date": str(data.loc[anchor_idx, "time"]),
            "index": int(anchor_idx),
            "bars_since_anchor": int(t_now),
            "price": anchor_price,
            "annual_volatility": anchor_vol,
        },
        "zone": {
            "name": price_zone,
            "color": price_zone_color,
            "sigma_move": sigma_move,
            "sigma_distance_abs": abs(sigma_move),
            "direction": "above" if sigma_move >= 0 else "below",
            "stretch_state": stretch_state,
        },
        "volatility": {
            "annualized": current_vol,
            "annualized_pct": current_vol * 100.0,
            "percentile_252": vol_percentile,
            "regime": vol_regime,
            "regime_color": vol_regime_color,
        },
        "current_boundaries": current_boundaries,
        "projection": {
            "bars_forward": config.proj_bars,
            "expected_move_pct": projected_moves_pct,
            "boundaries": projected_boundaries,
        },
        "context": {
            "bars_per_year": bars_per_year,
            "lock_mode": config.lock_mode,
            "lock_to_bull": config.lock_to_bull,
            "vol_length": config.vol_length,
            "pivot_len": config.pivot_len,
            "price_vs_anchor_pct": (current_price - anchor_price) / anchor_price * 100.0,
            "position_in_2_5sigma_band": float(position_in_25)
            if not np.isnan(position_in_25)
            else np.nan,
            "upper_2_5sigma_now": upper_25,
            "lower_2_5sigma_now": lower_25,
        },
        "summary": (
            f"{ticker} {freq}: {price_zone} ({price_zone_color}), "
            f"{abs(sigma_move):.2f}σ {'above' if sigma_move >= 0 else 'below'} anchor; "
            f"vol regime {vol_regime} ({vol_percentile:.1f} pct), "
            f"anchor {anchor_type} at {anchor_price:.2f}, "
            f"{config.proj_bars}-bar 1σ move +/-{projected_moves_pct['1sigma']:.2f}%."
        ),
    }

    return result


def format_projection_cone_report(result: dict[str, Any]) -> str:
    """Format projection cone analysis output as readable markdown report."""
    zone = result["zone"]
    vol = result["volatility"]
    anchor = result["anchor"]
    projection = result["projection"]
    context = result["context"]
    bounds = projection["boundaries"]

    return "\n".join(
        [
            f"{result['ticker']} {result['timeframe']} as of {result['as_of']}",
            f"Zone: {zone['name']} | Color: {zone['color']}",
            f"Sigma: {zone['sigma_distance_abs']:.2f}σ {zone['direction']} anchor | Stretch: {zone['stretch_state']}",
            f"Vol: {vol['annualized_pct']:.2f}% annualized | Regime: {vol['regime']} | Percentile: {vol['percentile_252']:.1f}",
            f"Anchor: {anchor['type']} at {anchor['price']:.2f} on {anchor['date']} | Bars since anchor: {anchor['bars_since_anchor']}",
            f"Price vs anchor: {context['price_vs_anchor_pct']:.2f}%",
            f"Current 1σ: {result['current_boundaries']['1sigma_lower']:.2f} to {result['current_boundaries']['1sigma_upper']:.2f}",
            f"Current 2σ: {result['current_boundaries']['2sigma_lower']:.2f} to {result['current_boundaries']['2sigma_upper']:.2f}",
            f"Current 3σ: {result['current_boundaries']['3sigma_lower']:.2f} to {result['current_boundaries']['3sigma_upper']:.2f}",
            f"{projection['bars_forward']}-bar 1σ: {bounds['1sigma_lower']:.2f} to {bounds['1sigma_upper']:.2f} | +/-{projection['expected_move_pct']['1sigma']:.2f}%",
            f"{projection['bars_forward']}-bar 2σ: {bounds['2sigma_lower']:.2f} to {bounds['2sigma_upper']:.2f} | +/-{projection['expected_move_pct']['2sigma']:.2f}%",
            f"{projection['bars_forward']}-bar 3σ: {bounds['3sigma_lower']:.2f} to {bounds['3sigma_upper']:.2f} | +/-{projection['expected_move_pct']['3sigma']:.2f}%",
        ]
    )


# Backward-compatible aliases
_resolve_bars_per_year = resolve_bars_per_year
_annual_volatility = calculate_annual_volatility
_percent_rank_current = calculate_percent_rank
_find_last_pivot = find_last_pivot
_cone_price = calculate_cone_price
_zone_from_sigma = get_zone_from_sigma
_vol_regime_from_percentile = get_vol_regime_from_percentile


if __name__ == "__main__":
    sample = analyze_projection_cone("RELIANCE.NS")
    print(format_projection_cone_report(sample))
    print(asdict(ProjectionConeConfig()))
