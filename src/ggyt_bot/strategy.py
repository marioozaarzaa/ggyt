from __future__ import annotations

from collections.abc import Sequence

from ggyt_bot.models import Signal, StrategyDecision
from ggyt_bot.settings import StrategyConfig


class MovingAverageCrossoverStrategy:
    """Simple transparent momentum strategy, intentionally conservative by default."""

    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    def decide(self, symbol: str, closes: Sequence[float]) -> StrategyDecision:
        needed = self.config.long_window
        if len(closes) < needed:
            return StrategyDecision(symbol, Signal.HOLD, 0.0, f"need at least {needed} closes")

        short_avg = sum(closes[-self.config.short_window :]) / self.config.short_window
        long_avg = sum(closes[-self.config.long_window :]) / self.config.long_window
        strength = (short_avg - long_avg) / long_avg if long_avg else 0.0

        if strength >= self.config.min_signal_strength:
            return StrategyDecision(symbol, Signal.BUY, strength, "short SMA above long SMA")
        if strength <= -self.config.min_signal_strength:
            return StrategyDecision(symbol, Signal.SELL, abs(strength), "short SMA below long SMA")
        return StrategyDecision(symbol, Signal.HOLD, abs(strength), "signal below threshold")
