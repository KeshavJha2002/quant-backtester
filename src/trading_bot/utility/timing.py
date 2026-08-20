from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

MARKET_TZ = ZoneInfo("Asia/Kolkata")
MARKET_CLOSE = time(15, 30)


def latest_complete_bar_index(time_values: Sequence[Any] | np.ndarray, freq: str) -> int | None:
    """Determine the index of the latest fully completed candle bar.

    For daily bars (freq='D'), today's bar is considered complete only after 15:30 IST
    or on weekends.
    For weekly bars (freq='W'), the current week's bar is considered complete only after
    Friday 15:30 IST or on weekends.
    """
    if len(time_values) == 0:
        return None

    timestamps: list[datetime] = []
    for value in time_values:
        ts = pd.to_datetime(value)
        if ts.tzinfo is None:
            ts = ts.tz_localize(MARKET_TZ)
        else:
            ts = ts.tz_convert(MARKET_TZ)
        timestamps.append(ts.to_pydatetime())

    now = datetime.now(MARKET_TZ)
    last_idx = len(timestamps) - 1
    last_ts = timestamps[last_idx]
    last_date = last_ts.date()
    today = now.date()

    if freq == "D":
        if last_date < today:
            return last_idx
        if last_date > today:
            return last_idx - 1 if last_idx > 0 else None
        if now.weekday() < 5 and now.time() < MARKET_CLOSE:
            return last_idx - 1 if last_idx > 0 else None
        return last_idx

    if freq == "W":
        current_week_start = today.fromordinal(today.toordinal() - today.weekday())
        if last_date < current_week_start:
            return last_idx
        if last_date > current_week_start:
            return last_idx - 1 if last_idx > 0 else None
        week_complete = now.weekday() > 4 or (now.weekday() == 4 and now.time() >= MARKET_CLOSE)
        if not week_complete:
            return last_idx - 1 if last_idx > 0 else None
        return last_idx

    return last_idx


# Backward-compatible alias
_latest_complete_bar_index = latest_complete_bar_index
