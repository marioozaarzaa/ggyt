from __future__ import annotations

from ggyt_bot.models import Signal, StrategyDecision
from ggyt_bot.settings import StrategyConfig
from ggyt_bot.strategies.strategy_base import StrategyBase, StrategyContext
from ggyt_bot.strategy import MovingAverageCrossoverStrategy


class SMAStrategy(StrategyBase):
    name = "sma"

    def __init__(self, config: StrategyConfig | None = None) -> None:
        self.config = config or StrategyConfig()
        self.parameters = {
            "short_window": self.config.short_window,
            "long_window": self.config.long_window,
            "min_signal_strength": self.config.min_signal_strength,
        }
        self._legacy = MovingAverageCrossoverStrategy(self.config)

    def generate_signal(self, context: StrategyContext) -> StrategyDecision:
        decision = self._legacy.decide(context.symbol, context.market_data.close)
        return self.validate_signal(decision, context)


class MultiIndicatorTrendStrategy(StrategyBase):
    name = "multi_indicator_trend"
    parameters = {
        "buy": "EMA20 > EMA50 > EMA200 AND 45 < RSI < 65 AND relative_volume > 1",
        "sell": "EMA20 < EMA50",
    }

    def generate_signal(self, context: StrategyContext) -> StrategyDecision:
        features = context.features
        required = [
            features.ema20,
            features.ema50,
            features.ema200,
            features.rsi14,
            features.relative_volume20,
        ]
        if any(value is None for value in required):
            return StrategyDecision(
                context.symbol, Signal.HOLD, 0.0, "insufficient indicator history"
            )

        assert features.ema20 is not None
        assert features.ema50 is not None
        assert features.ema200 is not None
        assert features.rsi14 is not None
        assert features.relative_volume20 is not None

        buy = (
            features.ema20 > features.ema50
            and features.ema50 > features.ema200
            and features.rsi14 > 45
            and features.rsi14 < 65
            and features.relative_volume20 > 1
        )
        sell = features.ema20 < features.ema50
        if buy:
            strength = (features.ema20 - features.ema50) / features.ema50
            return StrategyDecision(
                context.symbol, Signal.BUY, strength, "multi-indicator trend buy"
            )
        if sell:
            strength = (features.ema50 - features.ema20) / features.ema50
            return StrategyDecision(context.symbol, Signal.SELL, strength, "EMA20 below EMA50")
        return StrategyDecision(
            context.symbol, Signal.HOLD, 0.0, "multi-indicator filters not aligned"
        )
