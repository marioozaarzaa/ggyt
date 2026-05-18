from ggyt_bot.strategies.mean_reversion import MeanReversionStrategy
from ggyt_bot.strategies.momentum import MomentumStrategy
from ggyt_bot.strategies.sma import MultiIndicatorTrendStrategy, SMAStrategy
from ggyt_bot.strategies.strategy_base import StrategyBase, StrategyContext
from ggyt_bot.strategies.trend import TrendStrategy

STRATEGY_REGISTRY = {
    "sma": SMAStrategy,
    "multi_indicator_trend": MultiIndicatorTrendStrategy,
    "momentum": MomentumStrategy,
    "trend": TrendStrategy,
    "mean_reversion": MeanReversionStrategy,
}

__all__ = [
    "MeanReversionStrategy",
    "MomentumStrategy",
    "MultiIndicatorTrendStrategy",
    "SMAStrategy",
    "STRATEGY_REGISTRY",
    "StrategyBase",
    "StrategyContext",
    "TrendStrategy",
]
