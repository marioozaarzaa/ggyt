from __future__ import annotations

from ggyt_bot.models import Signal, StrategyDecision
from ggyt_bot.strategies.mean_reversion import MeanReversionStrategy
from ggyt_bot.strategies.momentum import MomentumStrategy
from ggyt_bot.strategies.strategy_base import StrategyBase, StrategyContext
from ggyt_bot.strategies.trend import TrendStrategy


class EnsembleStrategy(StrategyBase):
    name = "ensemble"
    parameters = {"buy_threshold": 1.0, "sell_threshold": -1.0}

    def __init__(self, strategies: list[StrategyBase] | None = None) -> None:
        self.strategies = strategies or [
            TrendStrategy(),
            MomentumStrategy(),
            MeanReversionStrategy(),
        ]

    def generate_signal(self, context: StrategyContext) -> StrategyDecision:
        decisions = [strategy.generate_signal(context) for strategy in self.strategies]
        total_score = sum(decision.score for decision in decisions)
        if total_score > 1:
            signal = Signal.BUY
        elif total_score < -1:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        reason = "; ".join(
            f"{strategy.name}={decision.score:.2f}"
            for strategy, decision in zip(self.strategies, decisions, strict=False)
        )
        return StrategyDecision(
            context.symbol,
            signal,
            abs(total_score),
            reason,
            confidence=min(1.0, abs(total_score) / 2),
            score=total_score,
        )
