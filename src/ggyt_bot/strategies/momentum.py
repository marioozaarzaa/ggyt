from __future__ import annotations

from ggyt_bot.models import Signal, StrategyDecision
from ggyt_bot.strategies.strategy_base import StrategyBase, StrategyContext


class MomentumStrategy(StrategyBase):
    name = "momentum"
    parameters = {"macd_histogram_positive": 0.3, "price_above_ema20": 0.2}

    def generate_signal(self, context: StrategyContext) -> StrategyDecision:
        features = context.features
        if features.macd_histogram is None or features.ema20 is None or features.last_close is None:
            return StrategyDecision(context.symbol, Signal.HOLD, 0.0, "insufficient momentum data")
        score = 0.0
        if features.macd_histogram > 0:
            score += 0.3
        else:
            score -= 0.3
        if features.last_close > features.ema20:
            score += 0.2
        else:
            score -= 0.2
        signal = Signal.BUY if score > 0.45 else Signal.SELL if score < -0.45 else Signal.HOLD
        return StrategyDecision(
            context.symbol,
            signal,
            abs(score),
            "momentum score",
            confidence=min(1.0, abs(score)),
            score=score,
        )
