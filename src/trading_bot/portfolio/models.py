from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass
class Position:
    ticker: str
    quantity: int
    avg_buy_price: float
    buy_date: str = field(default_factory=lambda: date.today().isoformat())
    initial_stop_loss: float = 0.0
    current_stop_loss: float = 0.0
    target_price: float = 0.0
    notes: str = ""
    pyramid_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Position:
        return cls(
            ticker=data["ticker"].strip().upper(),
            quantity=int(data.get("quantity", 1)),
            avg_buy_price=float(data.get("avg_buy_price", 0.0)),
            buy_date=str(data.get("buy_date", date.today().isoformat())),
            initial_stop_loss=float(data.get("initial_stop_loss", 0.0)),
            current_stop_loss=float(data.get("current_stop_loss", 0.0)),
            target_price=float(data.get("target_price", 0.0)),
            notes=str(data.get("notes", "")),
            pyramid_count=int(data.get("pyramid_count", 0)),
        )


@dataclass
class PositionEvaluation:
    ticker: str
    quantity: int
    avg_buy_price: float
    current_price: float
    invested_value: float
    current_value: float
    pnl_amount: float
    pnl_percent: float
    holding_days: int

    # Quantitative Indicators
    daily_sigma: float
    weekly_bull: bool
    daily_st_bull: bool
    above_200_sma: bool
    adx_value: float

    # Actionable Decision
    action: str  # "HOLD", "ADD", "TRIM", "EXIT"
    action_color: str  # "green", "blue", "orange", "red"
    suggested_stop_loss: float
    suggested_target_price: float
    risk_reward_ratio: float
    health_score: float  # 0 to 100

    # Structural Reasoning
    reasoning_summary: str
    structural_details: list[str]
