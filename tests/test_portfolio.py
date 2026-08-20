from __future__ import annotations

from pathlib import Path

import pytest

from trading_bot.portfolio import (
    PortfolioManager,
    Position,
    analyze_structural_patterns,
    calculate_position_size,
    compare_two_stocks_tie_breaker,
    evaluate_position,
)
from trading_bot.strategy.common import get_complete_bar_fetcher
from trading_bot.utility import MarketDataStore, get_fetch_data

FIXTURE_CACHE = Path(__file__).resolve().parent / "fixtures" / "data_cache"


@pytest.fixture
def fixture_fetcher():
    store = MarketDataStore(base_dir=FIXTURE_CACHE)
    return get_fetch_data(store=store)


def test_portfolio_manager_crud_and_budget(tmp_path: Path) -> None:
    json_file = tmp_path / "test_portfolio.json"
    pm = PortfolioManager(file_path=json_file)

    # 1. Budget update
    pm.update_budget(total_budget=800000.0, cash_balance=250000.0)
    assert pm.total_budget == 800000.0
    assert pm.cash_balance == 250000.0

    # 2. Add position
    pos = pm.add_or_update_position("SAMPLE.NS", quantity=100, buy_price=1000.0, buy_date="2026-08-01")
    assert pos.ticker == "SAMPLE.NS"
    assert pos.quantity == 100
    assert pos.avg_buy_price == 1000.0
    assert len(pm.list_positions()) == 1

    # 3. Add more to average
    pos2 = pm.add_or_update_position("SAMPLE.NS", quantity=100, buy_price=1200.0)
    assert pos2.quantity == 200
    assert pos2.avg_buy_price == 1100.0
    assert pos2.pyramid_count == 1

    # 4. Reload from file
    pm2 = PortfolioManager(file_path=json_file)
    assert len(pm2.list_positions()) == 1
    assert pm2.positions["SAMPLE.NS"].quantity == 200
    assert pm2.total_budget == 800000.0
    assert pm2.cash_balance == 250000.0

    # 5. Remove
    removed = pm2.remove_position("SAMPLE.NS")
    assert removed is True
    assert len(pm2.list_positions()) == 0


def test_position_evaluation(fixture_fetcher) -> None:
    complete_fetcher = get_complete_bar_fetcher(fixture_fetcher)
    pos = Position(ticker="SAMPLE.NS", quantity=50, avg_buy_price=950.0, buy_date="2026-08-01")

    eval_result = evaluate_position(pos, fixture_fetcher, complete_fetcher)
    assert eval_result.ticker == "SAMPLE.NS"
    assert eval_result.action in {"HOLD", "ADD", "TRIM", "EXIT"}
    assert eval_result.suggested_stop_loss > 0
    assert eval_result.suggested_target_price > 0
    assert 0 <= eval_result.health_score <= 100
    assert len(eval_result.structural_details) > 0


def test_structural_pattern_and_tie_breaker(fixture_fetcher) -> None:
    complete_fetcher = get_complete_bar_fetcher(fixture_fetcher)
    d_df = complete_fetcher("SAMPLE.NS", type="D")
    w_df = fixture_fetcher("SAMPLE.NS", type="W")

    analysis_a = analyze_structural_patterns(d_df, w_df, "SAMPLE.NS", sigma_move=-0.2)
    analysis_b = analyze_structural_patterns(d_df, w_df, "SAMPLE2.NS", sigma_move=1.5)

    assert analysis_a.vcp_compression_ratio > 0
    assert analysis_a.accumulation_volume_ratio > 0
    assert len(analysis_a.key_strengths) > 0 or len(analysis_a.key_risks) > 0

    comp = compare_two_stocks_tie_breaker(analysis_a, analysis_b)
    assert "winner" in comp
    assert "rationale" in comp
    assert comp["winner"] in {"SAMPLE.NS", "SAMPLE2.NS"}


def test_position_sizer(fixture_fetcher) -> None:
    complete_fetcher = get_complete_bar_fetcher(fixture_fetcher)
    d_df = complete_fetcher("SAMPLE.NS", type="D")

    # Test Swing Sizing (1-4w)
    rec_swing = calculate_position_size(
        ticker="SAMPLE.NS",
        daily_df=d_df,
        total_budget=500000.0,
        available_cash=200000.0,
        holding_period="Swing (1-4w)",
        risk_per_trade_pct=1.0,
    )
    assert rec_swing.recommended_shares > 0
    assert rec_swing.total_investment_amount <= 200000.0
    assert rec_swing.suggested_stop_loss < rec_swing.current_price
    assert rec_swing.target_price > rec_swing.current_price
    assert rec_swing.risk_reward_ratio > 0

    # Test Long-Term Sizing (>6m)
    rec_lt = calculate_position_size(
        ticker="SAMPLE.NS",
        daily_df=d_df,
        total_budget=500000.0,
        available_cash=200000.0,
        holding_period="Long-Term (>6m)",
        risk_per_trade_pct=1.5,
    )
    assert rec_lt.recommended_shares > 0
    assert rec_lt.suggested_stop_loss < rec_swing.suggested_stop_loss  # Wider stop for LT
