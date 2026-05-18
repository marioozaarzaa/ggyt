from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ggyt_bot.data.feature_engine import FeatureSet
from ggyt_bot.data.market_data import OHLCVSeries
from ggyt_bot.models import Signal, StrategyDecision


@dataclass(frozen=True)
class StrategyContext:
    symbol: str
    market_data: OHLCVSeries
    features: FeatureSet
    account_equity: float | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


class StrategyBase(ABC):
    name: str = "base"
    parameters: dict[str, Any] = {}

    @abstractmethod
    def generate_signal(self, context: StrategyContext) -> StrategyDecision: ...

    def validate_signal(
        self, decision: StrategyDecision, context: StrategyContext
    ) -> StrategyDecision:
        if decision.symbol != context.symbol:
            return StrategyDecision(context.symbol, Signal.HOLD, 0.0, "invalid symbol in signal")
        return decision
