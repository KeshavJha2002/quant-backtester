from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st

from trading_bot.portfolio import (
    PortfolioManager,
    analyze_structural_patterns,
    compare_two_stocks_tie_breaker,
    evaluate_position,
)
from trading_bot.projection_cone import (
    ProjectionConeConfig,
    calculate_sigma_move,
    find_last_pivot,
    resolve_bars_per_year,
)
from trading_bot.strategy.common import get_complete_bar_fetcher
from trading_bot.utility import (
    MarketDataStore,
    get_fetch_data,
    nifty50_ns,
    nifty150_ns,
    nifty250_ns,
    normalize_ticker,
    update_universe_cache,
)
from trading_bot.utility.indicators import (
    compute_st_trend_from_config,
    compute_triple_supertrend,
    sma,
)

st.set_page_config(
    page_title="Quantum Portfolio & Trading Decision Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1e88e5; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.05rem; color: #757575; margin-bottom: 1.5rem; }
    .badge-add { background-color: #2e7d32; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .badge-hold { background-color: #1976d2; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .badge-trim { background-color: #f57c00; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    .badge-exit { background-color: #c62828; color: white; padding: 4px 10px; border-radius: 6px; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_store_and_fetchers():
    store = MarketDataStore()
    fetcher = get_fetch_data(refresh=False, store=store)
    complete_fetcher = get_complete_bar_fetcher(fetcher)
    return store, fetcher, complete_fetcher


store, fetcher, complete_fetcher = get_store_and_fetchers()
pm = PortfolioManager()

# --- SIDEBAR ---
st.sidebar.markdown("## ⚙️ Portfolio & Scanner Control")

# 1. Refresh Data
if st.sidebar.button("🔄 Pull & Refresh Live Data", use_container_width=True, type="primary"):
    with st.spinner("Fetching latest live market data for N150 + N50 + N250..."):
        all_ticks = sorted(set(nifty150_ns + nifty50_ns + nifty250_ns))
        update_universe_cache(all_ticks, intervals=("D", "W"), store=store)
        st.sidebar.success("Market Data Refreshed Successfully!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ➕ Quick Add / Edit Position")
with st.sidebar.form("add_position_form", clear_on_submit=True):
    new_ticker = st.text_input("Ticker Symbol (e.g. HDFCBANK.NS)", "").strip().upper()
    col_q1, col_q2 = st.columns(2)
    new_qty = col_q1.number_input("Shares", min_value=1, value=10, step=1)
    new_price = col_q2.number_input("Avg Buy Price (₹)", min_value=0.1, value=100.0, step=10.0)
    new_date = st.date_input("Buy Date", value=date.today()).isoformat()
    new_notes = st.text_input("Notes / Thesis", "")
    submit_pos = st.form_submit_button("Save Position to Portfolio", use_container_width=True)

    if submit_pos and new_ticker:
        norm_t = normalize_ticker(new_ticker)
        pm.add_or_update_position(norm_t, int(new_qty), float(new_price), new_date, new_notes)
        st.sidebar.success(f"Added {norm_t} to Portfolio!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Local Time**: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`")
st.sidebar.markdown("Engine: **C7 Elite Quantum Supertrend MTF**")


# --- MAIN INTERFACE ---
st.markdown('<div class="main-header">⚡ Quantum Trading & Portfolio Decision Terminal</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Automated 4-State Position Management (HOLD / ADD / TRIM / EXIT), Deterministic Structural Reasoning & Multi-Timeframe Screener</div>', unsafe_allow_html=True)

tab_portfolio, tab_screener, tab_tiebreaker, tab_charts = st.tabs([
    "📊 Portfolio & Decision Center",
    "🔍 Daily & Weekly Screener",
    "⚖️ Structural Tie-Breaker",
    "📈 Projection Cone Visualizer",
])


# ===========================================================================
# TAB 1: PORTFOLIO & POSITION ACTION CENTER
# ===========================================================================
with tab_portfolio:
    positions = pm.list_positions()

    if not positions:
        st.info("Your portfolio is currently empty. Use the sidebar on the left to add your current stock holdings, or import from `holdings.csv`!")
    else:
        # Evaluate all positions
        with st.spinner("Evaluating portfolio holdings against live multi-timeframe engine..."):
            evaluations = [
                evaluate_position(pos, fetcher, complete_fetcher)
                for pos in positions
            ]

        # Top KPI Metrics
        total_invested = sum(e.invested_value for e in evaluations)
        total_current = sum(e.current_value for e in evaluations)
        total_pnl_amt = total_current - total_invested
        total_pnl_pct = (total_pnl_amt / total_invested * 100.0) if total_invested > 0 else 0.0

        count_add = sum(1 for e in evaluations if e.action == "ADD")
        count_hold = sum(1 for e in evaluations if e.action == "HOLD")
        count_trim = sum(1 for e in evaluations if e.action == "TRIM")
        count_exit = sum(1 for e in evaluations if e.action == "EXIT")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Invested", f"₹{total_invested:,.2f}")
        m2.metric("Current Value", f"₹{total_current:,.2f}")
        m3.metric("Total P&L", f"₹{total_pnl_amt:+,.2f}", f"{total_pnl_pct:+.2f}%")
        m4.metric("Active Holdings", f"{len(evaluations)} Stocks")
        m5.metric("Action Summary", f"🟢 {count_add} | ⚪ {count_hold} | 🟡 {count_trim} | 🔴 {count_exit}")

        st.markdown("---")
        st.markdown("### 📋 Position Action & Health Matrix")

        # Table Summary
        table_rows = []
        for e in evaluations:
            table_rows.append({
                "Action": f"{'🟢' if e.action=='ADD' else ('⚪' if e.action=='HOLD' else ('🟡' if e.action=='TRIM' else '🔴'))} {e.action}",
                "Ticker": e.ticker,
                "Shares": e.quantity,
                "Avg Buy": f"₹{e.avg_buy_price:,.2f}",
                "Current Price": f"₹{e.current_price:,.2f}",
                "P&L %": f"{e.pnl_percent:+.2f}%",
                "Cone Sigma": f"{e.daily_sigma:+.2f}σ",
                "Dynamic Stop": f"₹{e.suggested_stop_loss:,.2f}",
                "Target (+2.0σ)": f"₹{e.suggested_target_price:,.2f}",
                "Health Score": f"{e.health_score:.0f}/100",
                "Holding Days": f"{e.holding_days}d",
            })

        df_table = pd.DataFrame(table_rows)
        st.dataframe(df_table, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🔬 In-Depth Structural Reasoning & Position Cards")

        for e in evaluations:
            with st.expander(f"**{e.ticker}** — Verdict: **{e.action}** ({e.pnl_percent:+.1f}% P&L | Health: {e.health_score:.0f}/100)", expanded=(e.action in ["ADD", "TRIM", "EXIT"])):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"#### Recommendation: `{e.action}`")
                    st.markdown(f"**Verdict Rationale**: {e.reasoning_summary}")
                    st.markdown("**Key Structural Signals & Risk Analysis**:")
                    for d in e.structural_details:
                        st.markdown(f"- {d}")
                with c2:
                    st.markdown("#### Position Management")
                    st.markdown(f"- **Suggested Stop Loss**: ₹{e.suggested_stop_loss:,.2f}")
                    st.markdown(f"- **Target Price**: ₹{e.suggested_target_price:,.2f}")
                    st.markdown(f"- **Risk/Reward**: {e.risk_reward_ratio:.2f}x")
                    if st.button(f"❌ Remove {e.ticker}", key=f"del_{e.ticker}"):
                        pm.remove_position(e.ticker)
                        st.success(f"Removed {e.ticker}")
                        st.rerun()


# ===========================================================================
# TAB 2: DAILY & WEEKLY OPPORTUNITY SCREENER
# ===========================================================================
with tab_screener:
    st.markdown("### 🔍 Champion Strategy Screener (Daily C7 & Weekly C6)")
    st.markdown("Scans the entire selected universe on the **latest closed candle** and ranks candidates by Quantum Ranking Score.")

    col_s1, col_s2, col_s3 = st.columns([2, 2, 2])
    sel_universe = col_s1.selectbox("Equity Universe", ["N150 (Midcaps)", "N250 (Smallcaps)", "N50 (Largecaps)", "All Universes"], index=0)
    max_sigma_in = col_s2.slider("Max Valuation Sigma (Entry Floor)", min_value=-1.0, max_value=0.5, value=0.0, step=0.1)
    run_scan_btn = col_s3.button("⚡ Run Screener Scan Now", use_container_width=True, type="primary")

    if run_scan_btn:
        u_key = "N150" if "150" in sel_universe else ("N250" if "250" in sel_universe else ("N50" if "50" in sel_universe else "all"))
        tickers_to_scan = nifty150_ns if u_key == "N150" else (nifty250_ns if u_key == "N250" else (nifty50_ns if u_key == "N50" else sorted(set(nifty150_ns + nifty250_ns + nifty50_ns))))

        with st.spinner(f"Scanning {len(tickers_to_scan)} tickers for Daily & Weekly triggers..."):
            # Daily Scan
            daily_hits = []
            weekly_hits = []
            cone_cfg = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)

            for t in tickers_to_scan:
                try:
                    # Weekly Check
                    w_df = fetcher(t, type="W")
                    w_close = np.asarray(w_df["close"].values, float).ravel()
                    w_high = np.asarray(w_df["high"].values, float).ravel()
                    w_low = np.asarray(w_df["low"].values, float).ravel()
                    if len(w_close) < 25:
                        continue
                    w_t1, w_t2, w_t3 = compute_triple_supertrend(w_close, w_high, w_low)
                    w_bull = (w_t1[-1] == 1 or w_t2[-1] == 1 or w_t3[-1] == 1)

                    # Daily Check
                    d_df = complete_fetcher(t, type="D")
                    d_close = np.asarray(d_df["close"].values, float).ravel()
                    d_high = np.asarray(d_df["high"].values, float).ravel()
                    d_low = np.asarray(d_df["low"].values, float).ravel()
                    d_vol = np.asarray(d_df["volume"].values, float).ravel()
                    n = len(d_close)
                    if n < 200:
                        continue

                    d_fast = compute_st_trend_from_config(d_close, d_high, d_low, 10, 3.0, 1)
                    d_slow = compute_st_trend_from_config(d_close, d_high, d_low, 14, 3.5, 3)
                    d_sma200 = float(sma(d_close, 200)[-1])

                    # Sigma
                    bars_per_year = resolve_bars_per_year("D", cone_cfg.bars_per_year)
                    vol_s = pd.Series(np.log(d_close[1:] / d_close[:-1])).rolling(cone_cfg.vol_length).std() * np.sqrt(bars_per_year)
                    c_vol = float(vol_s.iloc[-1])
                    p_idx = find_last_pivot(d_high, d_low, cone_cfg.pivot_len, cone_cfg.lock_to_bull)
                    a_idx = p_idx if (cone_cfg.lock_mode and p_idx is not None) else (n - 1)
                    a_price = float(d_low[a_idx] if cone_cfg.lock_to_bull else d_high[a_idx]) if p_idx is not None else float(d_close[-1])
                    bars_s = max(n - 1 - a_idx, 1)
                    sig = calculate_sigma_move(float(d_close[-1]), a_price, c_vol if c_vol > 0 else 0.3, bars_s, bars_per_year)

                    # Daily Trigger
                    if (
                        w_bull
                        and d_fast[-2] == -1 and d_fast[-1] == 1 and d_slow[-1] == 1
                        and d_close[-1] >= d_sma200 * 0.98
                        and sig <= max_sigma_in
                    ):
                        patterns = analyze_structural_patterns(d_df, w_df, t, sigma_move=sig)
                        daily_hits.append({
                            "Ticker": t,
                            "Price": float(d_close[-1]),
                            "Cone Sigma": sig,
                            "VCP Ratio": patterns.vcp_compression_ratio,
                            "Acc Vol": patterns.accumulation_volume_ratio,
                            "Score": patterns.structural_score,
                            "Verdict": patterns.verdict,
                        })

                    # Weekly Trigger
                    if (
                        ((w_t1[-2] == -1 and w_t1[-1] == 1) or (w_t2[-2] == -1 and w_t2[-1] == 1))
                        and sig <= max_sigma_in
                    ):
                        patterns = analyze_structural_patterns(d_df, w_df, t, sigma_move=sig)
                        weekly_hits.append({
                            "Ticker": t,
                            "Price": float(w_close[-1]),
                            "Cone Sigma": sig,
                            "VCP Ratio": patterns.vcp_compression_ratio,
                            "Acc Vol": patterns.accumulation_volume_ratio,
                            "Score": patterns.structural_score,
                            "Verdict": patterns.verdict,
                        })
                except Exception:
                    continue

        st.markdown("#### 🏆 Section 1: Daily Champion (C7) Triggers")
        if daily_hits:
            df_d = pd.DataFrame(daily_hits).sort_values(by="Score", ascending=False)
            st.dataframe(df_d, use_container_width=True)
        else:
            st.info("No daily pullback buy triggers on the latest closed candle.")

        st.markdown("#### 🏆 Section 2: Weekly Champion (C6) Triggers")
        if weekly_hits:
            df_w = pd.DataFrame(weekly_hits).sort_values(by="Score", ascending=False)
            st.dataframe(df_w, use_container_width=True)
        else:
            st.info("No weekly breakout triggers on the latest closed candle.")


# ===========================================================================
# TAB 3: DETERMINISTIC STRUCTURAL TIE-BREAKER
# ===========================================================================
with tab_tiebreaker:
    st.markdown("### ⚖️ Head-to-Head Structural Pattern Tie-Breaker")
    st.markdown("When two stocks trigger with similar scores and you can only allocate capital to one, this engine performs a deterministic structural breakdown across 5 structural dimensions.")

    col_tb1, col_tb2 = st.columns(2)
    stock_a_input = col_tb1.text_input("Candidate Stock A (e.g. PETRONET.NS)", "PETRONET.NS").strip().upper()
    stock_b_input = col_tb2.text_input("Candidate Stock B (e.g. HDFCBANK.NS)", "HDFCBANK.NS").strip().upper()

    if st.button("⚖️ Compare Head-to-Head & Determine Superior Choice", type="primary", use_container_width=True):
        try:
            d_df_a = complete_fetcher(stock_a_input, type="D")
            w_df_a = fetcher(stock_a_input, type="W")
            d_df_b = complete_fetcher(stock_b_input, type="D")
            w_df_b = fetcher(stock_b_input, type="W")

            analysis_a = analyze_structural_patterns(d_df_a, w_df_a, stock_a_input)
            analysis_b = analyze_structural_patterns(d_df_b, w_df_b, stock_b_input)

            comp = compare_two_stocks_tie_breaker(analysis_a, analysis_b)

            st.success(f"### 🏆 Recommendation Verdict: Commit to **{comp['winner']}**")
            st.markdown(f"**Deterministic Rationale**: {comp['rationale']}")

            st.markdown("---")
            st.markdown("#### 📊 Side-by-Side Structural Matrix")

            metrics_df = pd.DataFrame({
                "Structural Metric": [
                    "Structural Quality Score (0-100)",
                    "VCP Volatility Contraction (ATR5/ATR20)",
                    "Institutional Accumulation Vol Ratio",
                    "Distance to 52-Week High (%)",
                    "20-Day Momentum Return (%)",
                    "Projection Cone Risk/Reward Ratio",
                    "Pattern Verdict",
                ],
                f"Stock A: {stock_a_input}": [
                    f"{analysis_a.structural_score:.1f} / 100",
                    f"{analysis_a.vcp_compression_ratio:.2f} ({'Coiled' if analysis_a.vcp_compression_ratio < 0.8 else 'Normal'})",
                    f"{analysis_a.accumulation_volume_ratio:.2f}x",
                    f"{analysis_a.distance_to_52w_high_pct:.1f}%",
                    f"{analysis_a.rs_momentum_pct:+.1f}%",
                    f"{analysis_a.cone_risk_reward_ratio:.2f}x",
                    analysis_a.verdict,
                ],
                f"Stock B: {stock_b_input}": [
                    f"{analysis_b.structural_score:.1f} / 100",
                    f"{analysis_b.vcp_compression_ratio:.2f} ({'Coiled' if analysis_b.vcp_compression_ratio < 0.8 else 'Normal'})",
                    f"{analysis_b.accumulation_volume_ratio:.2f}x",
                    f"{analysis_b.distance_to_52w_high_pct:.1f}%",
                    f"{analysis_b.rs_momentum_pct:+.1f}%",
                    f"{analysis_b.cone_risk_reward_ratio:.2f}x",
                    analysis_b.verdict,
                ],
            })
            st.dataframe(metrics_df, use_container_width=True, hide_index=True)

        except Exception as exc:
            st.error(f"Error evaluating stocks: {exc}")


# ===========================================================================
# TAB 4: INTERACTIVE PROJECTION CONE VISUALIZER
# ===========================================================================
with tab_charts:
    st.markdown("### 📈 Interactive Projection Cone & Multi-Timeframe Visualizer")
    chart_ticker = st.text_input("Enter Ticker to Visualize", "PETRONET.NS").strip().upper()

    if st.button("📊 Render Technical Chart", type="primary"):
        try:
            d_df = complete_fetcher(chart_ticker, type="D")
            close = np.asarray(d_df["close"].values, float)
            dates = pd.to_datetime(d_df["time"])

            sma50 = sma(close, min(50, len(close) // 2))
            sma200 = sma(close, min(200, len(close) // 2))

            chart_data = pd.DataFrame({
                "Date": dates[-120:],
                "Close Price": close[-120:],
                "50 SMA": sma50[-120:],
                "200 SMA": sma200[-120:],
            }).set_index("Date")

            st.line_chart(chart_data)
            st.success(f"Rendered latest 120-day chart for {chart_ticker}")
        except Exception as exc:
            st.error(f"Error rendering chart: {exc}")
