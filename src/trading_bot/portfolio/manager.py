from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from trading_bot.portfolio.models import Position
from trading_bot.utility import normalize_ticker

DEFAULT_PORTFOLIO_FILE = Path("data/portfolio.json")
DEFAULT_HOLDINGS_CSV = Path("holdings.csv")


class PortfolioManager:
    def __init__(self, file_path: Path | str = DEFAULT_PORTFOLIO_FILE):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.positions: dict[str, Position] = {}
        self.total_budget: float = 500000.0
        self.cash_balance: float = 100000.0
        self.load()

    def load(self) -> None:
        if self.file_path.exists():
            try:
                data = json.loads(self.file_path.read_text(encoding="utf-8"))
                self.total_budget = float(data.get("total_budget", 500000.0))
                self.cash_balance = float(data.get("cash_balance", 100000.0))
                raw_positions = data.get("positions", {})
                self.positions = {
                    normalize_ticker(k): Position.from_dict(v)
                    for k, v in raw_positions.items()
                }
                return
            except Exception as exc:
                print(f"Warning: could not read {self.file_path}: {exc}")

        # Fallback to holdings.csv if available for default portfolio
        if self.file_path == DEFAULT_PORTFOLIO_FILE and DEFAULT_HOLDINGS_CSV.exists():
            self.import_from_csv(DEFAULT_HOLDINGS_CSV)
        else:
            self.positions = {}

    def save(self) -> None:
        data = {
            "total_budget": self.total_budget,
            "cash_balance": self.cash_balance,
            "positions": {
                k: pos.to_dict() for k, pos in self.positions.items()
            },
        }
        self.file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def update_budget(self, total_budget: float | None = None, cash_balance: float | None = None) -> None:
        if total_budget is not None and total_budget > 0:
            self.total_budget = total_budget
        if cash_balance is not None and cash_balance >= 0:
            self.cash_balance = cash_balance
        self.save()

    def add_or_update_position(
        self,
        ticker: str,
        quantity: int,
        buy_price: float,
        buy_date: str | None = None,
        notes: str = "",
        stop_loss: float = 0.0,
        target_price: float = 0.0,
    ) -> Position:
        norm_ticker = normalize_ticker(ticker)
        if norm_ticker in self.positions:
            pos = self.positions[norm_ticker]
            # Average cost recalculation if adding quantity
            total_qty = pos.quantity + quantity
            if total_qty > 0:
                new_avg = ((pos.quantity * pos.avg_buy_price) + (quantity * buy_price)) / total_qty
            else:
                new_avg = buy_price
            pos.quantity = total_qty
            pos.avg_buy_price = new_avg
            pos.pyramid_count += 1
            if notes:
                pos.notes = notes
            if stop_loss > 0:
                pos.current_stop_loss = stop_loss
            if target_price > 0:
                pos.target_price = target_price
        else:
            pos = Position(
                ticker=norm_ticker,
                quantity=quantity,
                avg_buy_price=buy_price,
                buy_date=buy_date or date.today().isoformat(),
                initial_stop_loss=stop_loss,
                current_stop_loss=stop_loss,
                target_price=target_price,
                notes=notes,
            )
            self.positions[norm_ticker] = pos

        self.save()
        return pos

    def remove_position(self, ticker: str) -> bool:
        norm_ticker = normalize_ticker(ticker)
        if norm_ticker in self.positions:
            del self.positions[norm_ticker]
            self.save()
            return True
        return False

    def list_positions(self) -> list[Position]:
        return list(self.positions.values())

    def import_from_csv(self, csv_path: Path | str, clear_existing: bool = True) -> int:
        path = Path(csv_path)
        if not path.exists():
            return 0

        if clear_existing:
            self.positions = {}

        count = 0
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            # Check if header exists
            if reader.fieldnames and any("ticker" in f.lower() for f in reader.fieldnames):
                for row in reader:
                    ticker = row.get("ticker") or row.get("Ticker") or row.get("symbol")
                    if not ticker:
                        continue
                    qty = int(row.get("quantity") or row.get("qty") or row.get("Shares") or 1)
                    raw_price = (
                        row.get("avg_buy_price")
                        or row.get("price")
                        or row.get("avg_price")
                        or row.get("BuyPrice")
                        or row.get("Avg. ₹")
                        or "0.0"
                    )
                    price = float(raw_price) if str(raw_price).replace(".", "", 1).strip().isdigit() else 0.0
                    date_val = row.get("buy_date") or row.get("date") or ""
                    notes = row.get("notes", "")
                    self.add_or_update_position(ticker, qty, price, date_val, notes)
                    count += 1
            else:
                # Raw rows without header: TICKER,QTY,PRICE
                handle.seek(0)
                raw_reader = csv.reader(handle)
                for row in raw_reader:
                    if not row or not row[0].strip():
                        continue
                    ticker = row[0].strip()
                    qty = int(row[1]) if len(row) > 1 and row[1].strip().isdigit() else 1
                    price = float(row[2]) if len(row) > 2 and row[2].strip().replace(".", "", 1).isdigit() else 0.0
                    self.add_or_update_position(ticker, qty, price)
                    count += 1

        self.save()
        return count

    def export_to_csv(self, csv_path: Path | str) -> None:
        path = Path(csv_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["ticker", "quantity", "avg_buy_price", "buy_date", "current_stop_loss", "target_price", "notes"])
            for pos in self.positions.values():
                writer.writerow([pos.ticker, pos.quantity, pos.avg_buy_price, pos.buy_date, pos.current_stop_loss, pos.target_price, pos.notes])
