from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Signal(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class MarketBar:
    symbol: str
    close: float


@dataclass(frozen=True)
class StrategyDecision:
    symbol: str
    signal: Signal
    strength: float
    reason: str
    confidence: float = 0.0
    score: float = 0.0


@dataclass(frozen=True)
class AccountSnapshot:
    equity: float
    cash: float
    buying_power: float


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    market_value: float
    unrealized_pl: float
    qty: float
    avg_entry_price: float
    current_price: float
