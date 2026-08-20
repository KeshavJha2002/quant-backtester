from __future__ import annotations

import pytest
import yfinance as yf


def _fail_on_network(*args, **kwargs):
    raise AssertionError(
        "Network call to yfinance detected in non-network test. Tests must use local fixtures or mocks."
    )


@pytest.fixture(autouse=True)
def guard_against_network_calls(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    if "network" not in request.keywords:
        monkeypatch.setattr(yf, "download", _fail_on_network)
        monkeypatch.setattr("trading_bot.utility.yf.download", _fail_on_network)
