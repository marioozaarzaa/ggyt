from __future__ import annotations

from ggyt_bot.models import Signal, StrategyDecision
from ggyt_bot.strategies.strategy_base import StrategyBase, StrategyContext


class MeanReversionStrategy(StrategyBase):
    name = "mean_reversion"
    parameters = {"buy_rsi_below": 30, "sell_rsi_above": 70}

    def generate_signal(self, context: StrategyContext) -> StrategyDecision:
        rsi = context.features.rsi14
        if rsi is None:
            return StrategyDecision(context.symbol, Signal.HOLD, 0.0, "insufficient RSI history")
        if rsi < 30:
            return StrategyDecision(context.symbol, Signal.BUY, (30 - rsi) / 30, "RSI oversold")
        if rsi > 70:
            return StrategyDecision(context.symbol, Signal.SELL, (rsi - 70) / 30, "RSI overbought")
        return StrategyDecision(context.symbol, Signal.HOLD, 0.0, "RSI neutral")
