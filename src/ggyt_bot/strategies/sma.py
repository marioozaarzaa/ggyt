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
        score = decision.strength if decision.signal is Signal.BUY else -decision.strength
        if decision.signal is Signal.HOLD:
            score = 0.0
        decision = StrategyDecision(
            decision.symbol,
            decision.signal,
            decision.strength,
            decision.reason,
            confidence=min(1.0, abs(score)),
            score=score,
        )
        return self.validate_signal(decision, context)


class MultiIndicatorTrendStrategy(StrategyBase):
    name = "multi_indicator_trend"
    parameters = {
        "buy": "score > 0.8 from EMA alignment, RSI, relative volume and volatility",
        "sell": "EMA20 < EMA50 or score < -0.8",
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

        score = 0.0
        reasons: list[str] = []
        ema_alignment = features.ema20 > features.ema50 > features.ema200
        if ema_alignment:
            score += 0.4
            reasons.append("EMA bullish alignment")
        elif features.ema20 < features.ema50:
            score -= 1.0
            reasons.append("EMA20 below EMA50")

        if 45 < features.rsi14 < 65:
            score += 0.2
            reasons.append("RSI in trend continuation range")
        elif features.rsi14 > 75:
            score -= 0.2
            reasons.append("RSI overheated")

        if features.relative_volume20 > 1:
            score += 0.2
            reasons.append("relative volume confirms")

        volatility_ok = features.volatility20 is None or features.volatility20 < 0.30
        if volatility_ok:
            score += 0.2
            reasons.append("volatility acceptable")
        else:
            score -= 0.4
            reasons.append("volatility elevated")

        if score > 0.8:
            signal = Signal.BUY
        elif score < -0.8:
            signal = Signal.SELL
        else:
            signal = Signal.HOLD
        reason = "; ".join(reasons) if reasons else "multi-indicator filters not aligned"
        return StrategyDecision(
            context.symbol,
            signal,
            abs(score),
            reason,
            confidence=min(1.0, abs(score)),
            score=score,
        )
