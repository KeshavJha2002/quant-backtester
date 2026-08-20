from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Select,
    TabbedContent,
    TabPane,
)

from trading_bot.portfolio import (
    PortfolioManager,
    PositionEvaluation,
    SizingRecommendation,
    analyze_structural_patterns,
    calculate_position_size,
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


class EditBudgetModal(ModalScreen[bool]):
    """Modal dialog to update Total Account Budget and Cash Balance."""

    def __init__(self, current_budget: float, current_cash: float) -> None:
        super().__init__()
        self.current_budget = current_budget
        self.current_cash = current_cash

    def compose(self) -> ComposeResult:
        yield Container(
            Label("💰 Update Capital Budget & Cash Balance", id="modal_title"),
            Label("Total Account Capital / Budget (₹):"),
            Input(placeholder="500000", value=str(int(self.current_budget)), id="inp_budget"),
            Label("Available Liquid Cash Balance (₹):"),
            Input(placeholder="100000", value=str(int(self.current_cash)), id="inp_cash"),
            Horizontal(
                Button("Save Budget", variant="success", id="btn_save_budget"),
                Button("Cancel", variant="error", id="btn_cancel_budget"),
                classes="modal_buttons",
            ),
            id="modal_container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save_budget":
            b_val = self.query_one("#inp_budget", Input).value.strip()
            c_val = self.query_one("#inp_cash", Input).value.strip()

            if b_val.replace(".", "", 1).isdigit() and c_val.replace(".", "", 1).isdigit():
                pm = PortfolioManager()
                pm.update_budget(total_budget=float(b_val), cash_balance=float(c_val))
                self.dismiss(True)
                return
            self.dismiss(False)
        else:
            self.dismiss(False)


class AddPositionModal(ModalScreen[bool]):
    """Modal dialog to add or edit a position directly inside TUI."""

    def compose(self) -> ComposeResult:
        yield Container(
            Label("➕ Add New Holding to Portfolio", id="modal_title"),
            Label("Ticker Symbol (e.g. RELIANCE.NS, PETRONET.NS):"),
            Input(placeholder="TICKER.NS", id="inp_ticker"),
            Label("Quantity (Shares):"),
            Input(placeholder="10", value="10", id="inp_qty"),
            Label("Average Buy Price (₹):"),
            Input(placeholder="100.0", value="100.0", id="inp_price"),
            Label("Notes / Strategy Tag:"),
            Input(placeholder="Optional notes", value="C7 Quantum ST", id="inp_notes"),
            Horizontal(
                Button("Save Position", variant="success", id="btn_save"),
                Button("Cancel", variant="error", id="btn_cancel"),
                classes="modal_buttons",
            ),
            id="modal_container",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_save":
            ticker_val = self.query_one("#inp_ticker", Input).value.strip().upper()
            qty_val = self.query_one("#inp_qty", Input).value.strip()
            price_val = self.query_one("#inp_price", Input).value.strip()
            notes_val = self.query_one("#inp_notes", Input).value.strip()

            if ticker_val and qty_val.isdigit() and price_val.replace(".", "", 1).isdigit():
                norm_t = normalize_ticker(ticker_val)
                pm = PortfolioManager()
                pm.add_or_update_position(
                    ticker=norm_t,
                    quantity=int(qty_val),
                    buy_price=float(price_val),
                    buy_date=date.today().isoformat(),
                    notes=notes_val,
                )
                pm.export_to_csv("holdings.csv")
                self.dismiss(True)
                return
            self.dismiss(False)
        else:
            self.dismiss(False)


class QuantumTradingTUI(App):
    """Full-featured Terminal User Interface for Portfolio & Trading Decisions."""

    TITLE = "⚡ Quantum Trading & Portfolio Terminal"
    SUB_TITLE = "Multi-Timeframe Engine | Position Sizer | 4-State Decisions"
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
    }
    Header {
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
    }
    Footer {
        background: #1e293b;
        color: #94a3b8;
    }
    #budget_banner {
        height: 3;
        background: #0284c7;
        color: #ffffff;
        padding: 0 2;
        content-align: center middle;
        text-style: bold;
    }
    #kpi_container {
        height: 4;
        background: #1e293b;
        border: round #38bdf8;
        padding: 0 2;
        margin: 1 1;
    }
    .kpi_box {
        width: 1fr;
        content-align: center middle;
        text-style: bold;
    }
    DataTable {
        height: 13;
        background: #0f172a;
        border: round #475569;
        margin: 1 1;
    }
    #detail_pane {
        height: 11;
        background: #1e293b;
        border: round #38bdf8;
        padding: 1 2;
        margin: 0 1 1 1;
    }
    #modal_container {
        width: 60;
        height: auto;
        background: #1e293b;
        border: thick #38bdf8;
        padding: 2 3;
        align: center middle;
    }
    #modal_title {
        text-style: bold;
        color: #38bdf8;
        margin-bottom: 1;
    }
    .modal_buttons {
        margin-top: 1;
        align: right middle;
    }
    .sizer_inputs {
        height: 4;
        margin: 1 1;
    }
    #sizer_result_pane {
        height: 16;
        background: #1e293b;
        border: round #22c55e;
        padding: 1 2;
        margin: 1 1;
    }
    """

    BINDINGS = [
        Binding("1", "switch_tab('tab_portfolio')", "Portfolio", show=True),
        Binding("2", "switch_tab('tab_screener')", "Screener", show=True),
        Binding("3", "switch_tab('tab_sizer')", "Position Sizer", show=True),
        Binding("4", "switch_tab('tab_tiebreaker')", "Tie-Breaker", show=True),
        Binding("b", "edit_budget", "Edit Budget", show=True),
        Binding("a", "add_holding", "Add Stock", show=True),
        Binding("d", "delete_holding", "Delete Selected", show=True),
        Binding("r", "refresh_data", "Refresh Data", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.pm = PortfolioManager()
        self.store = MarketDataStore()
        self.fetcher = get_fetch_data(refresh=False, store=self.store)
        self.complete_fetcher = get_complete_bar_fetcher(self.fetcher)
        self.evaluations: list[PositionEvaluation] = []
        self.current_eval_map: dict[str, PositionEvaluation] = {}
        self.last_sizer_rec: SizingRecommendation | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Label("💰 Capital Budget: ₹5,00,000 | Invested: ₹0 | Cash Available: ₹5,00,000", id="budget_banner")

        with TabbedContent(initial="tab_portfolio", id="main_tabs"):
            # --- TAB 1: PORTFOLIO ---
            with TabPane("📊 Portfolio & Decisions", id="tab_portfolio"):
                with Horizontal(id="kpi_container"):
                    yield Label("Loading portfolio...", id="kpi_invested", classes="kpi_box")
                    yield Label("...", id="kpi_current", classes="kpi_box")
                    yield Label("...", id="kpi_pnl", classes="kpi_box")
                    yield Label("...", id="kpi_actions", classes="kpi_box")

                yield DataTable(id="portfolio_table", cursor_type="row")

                with VerticalScroll(id="detail_pane"):
                    yield Markdown("### Select a holding above to view structural reasoning & action verdict.", id="detail_md")

            # --- TAB 2: SCREENER ---
            with TabPane("🔍 Daily & Weekly Screener", id="tab_screener"):
                with Horizontal(classes="screener_controls"):
                    yield Select(
                        [("N150 Midcaps", "N150"), ("N250 Smallcaps", "N250"), ("N50 Largecaps", "N50"), ("All Universes", "all")],
                        value="N150",
                        id="screener_universe",
                    )
                    yield Button("⚡ Run Champion Scan Now", variant="primary", id="btn_run_scan")

                yield DataTable(id="screener_table", cursor_type="row")
                with VerticalScroll(id="screener_detail_pane"):
                    yield Markdown("### Screener triggers on the last closed candle will appear here.", id="screener_md")

            # --- TAB 3: POSITION SIZER & BUDGET ALLOCATOR ---
            with TabPane("🧮 Position Sizer & Budget Calculator", id="tab_sizer"):
                with Horizontal(classes="sizer_inputs"):
                    yield Input(placeholder="Stock Ticker (e.g. PETRONET.NS)", value="PETRONET.NS", id="sizer_ticker")
                    yield Select(
                        [
                            ("Swing Trade (1-4 Weeks)", "Swing (1-4w)"),
                            ("Positional Trend (1-6 Months)", "Positional (1-6m)"),
                            ("Long-Term Compounder (>6 Months)", "Long-Term (>6m)"),
                        ],
                        value="Positional (1-6m)",
                        id="sizer_horizon",
                    )
                    yield Input(placeholder="Risk % (default: 1.0)", value="1.0", id="sizer_risk_pct")
                    yield Button("🧮 Calculate Optimal Quantity", variant="success", id="btn_calc_size")

                with VerticalScroll(id="sizer_result_pane"):
                    yield Markdown("### Enter a stock ticker and holding horizon above to calculate optimal shares.", id="sizer_md")

            # --- TAB 4: TIE-BREAKER ---
            with TabPane("⚖️ Structural Tie-Breaker", id="tab_tiebreaker"):
                with Horizontal():
                    yield Input(placeholder="Stock A (e.g. PETRONET.NS)", value="PETRONET.NS", id="tb_stock_a")
                    yield Input(placeholder="Stock B (e.g. HDFCBANK.NS)", value="HDFCBANK.NS", id="tb_stock_b")
                    yield Button("⚖️ Compare Head-to-Head", variant="warning", id="btn_compare")

                with VerticalScroll(id="tiebreaker_result_pane"):
                    yield Markdown("### Enter two stocks above to run deterministic 5-point structural comparison.", id="tb_md")

        yield Footer()

    def on_mount(self) -> None:
        self.setup_tables()
        self.load_and_evaluate_portfolio()

    def setup_tables(self) -> None:
        p_table = self.query_one("#portfolio_table", DataTable)
        p_table.add_columns("Action", "Ticker", "Qty", "Avg Buy (₹)", "Current (₹)", "P&L %", "Cone Sigma", "Dynamic Stop", "Target (+2σ)", "Score")

        s_table = self.query_one("#screener_table", DataTable)
        s_table.add_columns("Timeframe", "Segment", "Ticker", "Price (₹)", "Sigma", "ADX", "Vol Ratio", "Quantum Score", "Trigger Setup")

    def load_and_evaluate_portfolio(self) -> None:
        self.pm.load()
        positions = self.pm.list_positions()
        p_table = self.query_one("#portfolio_table", DataTable)
        p_table.clear()

        self.evaluations = []
        self.current_eval_map = {}

        total_inv = 0.0
        total_curr = 0.0
        add_c = 0
        hold_c = 0
        trim_c = 0
        exit_c = 0

        for pos in positions:
            ev = evaluate_position(pos, self.fetcher, self.complete_fetcher)
            self.evaluations.append(ev)
            self.current_eval_map[ev.ticker] = ev

            total_inv += ev.invested_value
            total_curr += ev.current_value

            if ev.action == "ADD":
                action_styled = Text("🟢 ADD", style="bold green")
                add_c += 1
            elif ev.action == "HOLD":
                action_styled = Text("⚪ HOLD", style="bold cyan")
                hold_c += 1
            elif ev.action == "TRIM":
                action_styled = Text("🟡 TRIM", style="bold yellow")
                trim_c += 1
            else:
                action_styled = Text("🔴 EXIT", style="bold red")
                exit_c += 1

            pnl_style = "bold green" if ev.pnl_percent >= 0 else "bold red"
            pnl_styled = Text(f"{ev.pnl_percent:+.2f}%", style=pnl_style)

            p_table.add_row(
                action_styled,
                Text(ev.ticker, style="bold white"),
                str(ev.quantity),
                f"₹{ev.avg_buy_price:,.2f}",
                f"₹{ev.current_price:,.2f}",
                pnl_styled,
                f"{ev.daily_sigma:+.2f}σ",
                f"₹{ev.suggested_stop_loss:,.2f}",
                f"₹{ev.suggested_target_price:,.2f}",
                f"{ev.health_score:.0f}/100",
                key=ev.ticker,
            )

        tot_pnl = total_curr - total_inv
        tot_pct = (tot_pnl / total_inv * 100.0) if total_inv > 0 else 0.0

        # Calculate Available Cash & Budget
        total_budget = self.pm.total_budget
        # Cash available = total_budget - total_current
        cash_avail = max(0.0, total_budget - total_curr)
        util_pct = (total_curr / total_budget * 100.0) if total_budget > 0 else 0.0

        banner_text = (
            f"💰 Total Budget: ₹{total_budget:,.2f}  |  "
            f"Current Holdings: ₹{total_curr:,.2f} ({util_pct:.1f}% Utilized)  |  "
            f"Available Cash: ₹{cash_avail:,.2f}  [Press 'b' to edit]"
        )
        self.query_one("#budget_banner", Label).update(banner_text)

        pnl_color = "green" if tot_pnl >= 0 else "red"
        self.query_one("#kpi_invested", Label).update(f"Invested: ₹{total_inv:,.2f}")
        self.query_one("#kpi_current", Label).update(f"Current: ₹{total_curr:,.2f}")
        self.query_one("#kpi_pnl", Label).update(f"P&L: [{pnl_color}]₹{tot_pnl:+,.2f} ({tot_pct:+.2f}%)[/{pnl_color}]")
        self.query_one("#kpi_actions", Label).update(f"🟢 {add_c} | ⚪ {hold_c} | 🟡 {trim_c} | 🔴 {exit_c}")

        if self.evaluations:
            self.show_position_detail(self.evaluations[0])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.data_table.id == "portfolio_table":
            ticker = str(event.row_key.value)
            if ticker in self.current_eval_map:
                self.show_position_detail(self.current_eval_map[ticker])
        elif event.data_table.id == "screener_table":
            ticker = str(event.row_key.value)
            self.query_one("#sizer_ticker", Input).value = ticker
            self.query_one("#screener_md", Markdown).update(
                f"### Triggered Stock: `{ticker}`\n- Switch to `[3] Position Sizer` to calculate exact shares to buy, or press `[a]` to add directly."
            )

    def show_position_detail(self, ev: PositionEvaluation) -> None:
        md_lines = [
            f"### **{ev.ticker}** — Decision: `{ev.action}` | P&L: `{ev.pnl_percent:+.2f}%` | Health Score: `{ev.health_score:.0f}/100`",
            f"- **Verdict Rationale**: {ev.reasoning_summary}",
            f"- **Suggested Stop Loss**: ₹{ev.suggested_stop_loss:,.2f} | **Profit Target (+2σ)**: ₹{ev.suggested_target_price:,.2f} | **Risk/Reward**: {ev.risk_reward_ratio:.2f}x",
            "",
            "**Key Structural Signals & Risk Analysis**:",
        ]
        for d in ev.structural_details:
            md_lines.append(f"- {d}")

        self.query_one("#detail_md", Markdown).update("\n".join(md_lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_run_scan":
            self.run_screener_scan()
        elif event.button.id == "btn_calc_size":
            self.run_position_sizer()
        elif event.button.id == "btn_compare":
            self.run_tie_breaker()

    def run_position_sizer(self) -> None:
        ticker_input = self.query_one("#sizer_ticker", Input).value.strip().upper()
        if not ticker_input:
            return

        horizon = self.query_one("#sizer_horizon", Select).value
        risk_str = self.query_one("#sizer_risk_pct", Input).value.strip()
        risk_pct = float(risk_str) if risk_str.replace(".", "", 1).isdigit() else 1.0

        norm_t = normalize_ticker(ticker_input)
        try:
            d_df = self.complete_fetcher(norm_t, type="D")
            # Current available cash
            total_curr = sum(ev.current_value for ev in self.evaluations)
            avail_cash = max(0.0, self.pm.total_budget - total_curr)

            rec = calculate_position_size(
                ticker=norm_t,
                daily_df=d_df,
                total_budget=self.pm.total_budget,
                available_cash=avail_cash,
                holding_period=str(horizon),
                risk_per_trade_pct=risk_pct,
            )
            self.last_sizer_rec = rec

            md = [
                f"### 🧮 Recommended Position Size: **`{rec.recommended_shares}` Shares** for **{rec.ticker}**",
                f"- **Current Market Price**: ₹{rec.current_price:,.2f}",
                f"- **Total Capital Required**: **₹{rec.total_investment_amount:,.2f}** ({rec.portfolio_allocation_pct:.1f}% of Total Budget)",
                f"- **Calculated Stop Loss Floor**: **₹{rec.suggested_stop_loss:,.2f}** (-{rec.stop_distance_pct:.1f}%)",
                f"- **Projection Cone Target Price**: **₹{rec.target_price:,.2f}** (+{rec.upside_potential_pct:.1f}% upside)",
                f"- **Trade Risk-to-Reward Ratio**: **{rec.risk_reward_ratio:.2f}x**",
                f"- **Total Capital at Risk**: **₹{rec.capital_at_risk_amount:,.2f}** ({rec.capital_at_risk_pct:.2f}% of Account Budget)",
                "",
                "---",
                "#### 🔬 Quantitative Sizing Rationale:",
                f"{rec.sizing_rationale}",
                "",
                "**Risk Parameter Breakdown**:",
            ]
            for note in rec.risk_notes:
                md.append(f"- {note}")

            md.append("\n*Tip: Press `[a]` to open Add Stock dialog and enter these shares directly into your portfolio.*")
            self.query_one("#sizer_md", Markdown).update("\n".join(md))

        except Exception as exc:
            self.query_one("#sizer_md", Markdown).update(f"### Error sizing stock `{norm_t}`: {exc}")

    def run_screener_scan(self) -> None:
        univ = self.query_one("#screener_universe", Select).value
        s_table = self.query_one("#screener_table", DataTable)
        s_table.clear()

        tickers = nifty150_ns if univ == "N150" else (nifty250_ns if univ == "N250" else (nifty50_ns if univ == "N50" else sorted(set(nifty150_ns + nifty250_ns + nifty50_ns))))
        cone_cfg = ProjectionConeConfig(lock_mode=True, lock_to_bull=False)
        found_count = 0

        for t in tickers:
            try:
                w_df = self.fetcher(t, type="W")
                w_close = np.asarray(w_df["close"].values, float).ravel()
                w_high = np.asarray(w_df["high"].values, float).ravel()
                w_low = np.asarray(w_df["low"].values, float).ravel()
                if len(w_close) < 25:
                    continue
                w_t1, w_t2, w_t3 = compute_triple_supertrend(w_close, w_high, w_low)
                w_bull = (w_t1[-1] == 1 or w_t2[-1] == 1 or w_t3[-1] == 1)

                d_df = self.complete_fetcher(t, type="D")
                d_close = np.asarray(d_df["close"].values, float).ravel()
                d_high = np.asarray(d_df["high"].values, float).ravel()
                d_low = np.asarray(d_df["low"].values, float).ravel()
                n = len(d_close)
                if n < 200:
                    continue

                d_fast = compute_st_trend_from_config(d_close, d_high, d_low, 10, 3.0, 1)
                d_slow = compute_st_trend_from_config(d_close, d_high, d_low, 14, 3.5, 3)
                sma200 = float(sma(d_close, 200)[-1])

                bars_per_year = resolve_bars_per_year("D", cone_cfg.bars_per_year)
                vol_s = pd.Series(np.log(d_close[1:] / d_close[:-1])).rolling(cone_cfg.vol_length).std() * np.sqrt(bars_per_year)
                c_vol = float(vol_s.iloc[-1])
                p_idx = find_last_pivot(d_high, d_low, cone_cfg.pivot_len, cone_cfg.lock_to_bull)
                a_idx = p_idx if (cone_cfg.lock_mode and p_idx is not None) else (n - 1)
                a_price = float(d_low[a_idx] if cone_cfg.lock_to_bull else d_high[a_idx]) if p_idx is not None else float(d_close[-1])
                bars_s = max(n - 1 - a_idx, 1)
                sig = calculate_sigma_move(float(d_close[-1]), a_price, c_vol if c_vol > 0 else 0.3, bars_s, bars_per_year)

                if (
                    w_bull
                    and d_fast[-2] == -1 and d_fast[-1] == 1 and d_slow[-1] == 1
                    and d_close[-1] >= sma200 * 0.98
                    and sig <= 0.0
                ):
                    patterns = analyze_structural_patterns(d_df, w_df, t, sigma_move=sig)
                    s_table.add_row(
                        "Daily C7",
                        univ,
                        t,
                        f"₹{d_close[-1]:,.2f}",
                        f"{sig:+.2f}σ",
                        f"{patterns.rs_momentum_pct:.1f}",
                        f"{patterns.accumulation_volume_ratio:.2f}x",
                        f"{patterns.structural_score:.1f}",
                        "ST Pullback Buy in Weekly Bull",
                        key=t,
                    )
                    found_count += 1

                if (
                    ((w_t1[-2] == -1 and w_t1[-1] == 1) or (w_t2[-2] == -1 and w_t2[-1] == 1))
                    and sig <= 0.0
                ):
                    patterns = analyze_structural_patterns(d_df, w_df, t, sigma_move=sig)
                    s_table.add_row(
                        "Weekly C6",
                        univ,
                        t,
                        f"₹{w_close[-1]:,.2f}",
                        f"{sig:+.2f}σ",
                        f"{patterns.rs_momentum_pct:.1f}",
                        f"{patterns.accumulation_volume_ratio:.2f}x",
                        f"{patterns.structural_score:.1f}",
                        "Weekly Supertrend Breakout",
                        key=t,
                    )
                    found_count += 1
            except Exception:
                continue

        self.query_one("#screener_md", Markdown).update(
            f"### Scan Complete: Found **{found_count}** trigger(s) on `{univ}`.\nSelect any row above to view details or press `[a]` to add to portfolio."
        )

    def run_tie_breaker(self) -> None:
        a_sym = self.query_one("#tb_stock_a", Input).value.strip().upper()
        b_sym = self.query_one("#tb_stock_b", Input).value.strip().upper()

        if not a_sym or not b_sym:
            return

        try:
            d_df_a = self.complete_fetcher(a_sym, type="D")
            w_df_a = self.fetcher(a_sym, type="W")
            d_df_b = self.complete_fetcher(b_sym, type="D")
            w_df_b = self.fetcher(b_sym, type="W")

            analysis_a = analyze_structural_patterns(d_df_a, w_df_a, a_sym)
            analysis_b = analyze_structural_patterns(d_df_b, w_df_b, b_sym)

            comp = compare_two_stocks_tie_breaker(analysis_a, analysis_b)

            md = [
                f"### 🏆 Deterministic Verdict: Commit to **`{comp['winner']}`**",
                f"**Rationale**: {comp['rationale']}",
                "",
                f"| Metric | **{a_sym}** | **{b_sym}** |",
                "|---|---|---|",
                f"| Structural Quality Score | **{analysis_a.structural_score:.1f} / 100** | **{analysis_b.structural_score:.1f} / 100** |",
                f"| VCP Compression Ratio | `{analysis_a.vcp_compression_ratio:.2f}` | `{analysis_b.vcp_compression_ratio:.2f}` |",
                f"| Accumulation Vol Ratio | `{analysis_a.accumulation_volume_ratio:.2f}x` | `{analysis_b.accumulation_volume_ratio:.2f}x` |",
                f"| Distance to 52w High | `{analysis_a.distance_to_52w_high_pct:.1f}%` | `{analysis_b.distance_to_52w_high_pct:.1f}%` |",
                f"| Cone Risk/Reward Ratio | `{analysis_a.cone_risk_reward_ratio:.2f}x` | `{analysis_b.cone_risk_reward_ratio:.2f}x` |",
                f"| Pattern Verdict | *{analysis_a.verdict}* | *{analysis_b.verdict}* |",
            ]
            self.query_one("#tb_md", Markdown).update("\n".join(md))
        except Exception as exc:
            self.query_one("#tb_md", Markdown).update(f"### Error comparing stocks: `{exc}`")

    def action_switch_tab(self, tab_id: str) -> None:
        tabs = self.query_one("#main_tabs", TabbedContent)
        tabs.active = tab_id

    def action_edit_budget(self) -> None:
        def _after_budget(saved: bool) -> None:
            if saved:
                self.load_and_evaluate_portfolio()

        total_curr = sum(ev.current_value for ev in self.evaluations)
        cash_avail = max(0.0, self.pm.total_budget - total_curr)
        self.push_screen(EditBudgetModal(self.pm.total_budget, cash_avail), _after_budget)

    def action_add_holding(self) -> None:
        def _after_add(saved: bool) -> None:
            if saved:
                self.load_and_evaluate_portfolio()

        self.push_screen(AddPositionModal(), _after_add)

    def action_delete_holding(self) -> None:
        p_table = self.query_one("#portfolio_table", DataTable)
        if p_table.cursor_row is not None:
            try:
                row_key = p_table.coordinate_to_cell_key((p_table.cursor_row, 0)).row_key
                ticker = str(row_key.value)
                self.pm.remove_position(ticker)
                self.pm.export_to_csv("holdings.csv")
                self.load_and_evaluate_portfolio()
            except Exception:
                pass

    def action_refresh_data(self) -> None:
        self.notify("Refreshing live market data across N50 + N150 + N250...")
        all_ticks = sorted(set(nifty150_ns + nifty50_ns + nifty250_ns))
        update_universe_cache(all_ticks, intervals=("D", "W"), store=self.store)
        self.load_and_evaluate_portfolio()
        self.notify("Live Market Data Refreshed Successfully!")


def main() -> None:
    app = QuantumTradingTUI()
    app.run()


if __name__ == "__main__":
    main()
