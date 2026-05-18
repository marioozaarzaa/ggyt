from ggyt_bot.models import Signal
from ggyt_bot.settings import StrategyConfig
from ggyt_bot.strategy import MovingAverageCrossoverStrategy


def test_buy_signal_when_short_average_exceeds_long_average() -> None:
    strategy = MovingAverageCrossoverStrategy(
        StrategyConfig(short_window=3, long_window=5, min_signal_strength=0.001)
    )

    decision = strategy.decide("SPY", [10, 10, 10, 11, 12])

    assert decision.signal is Signal.BUY
    assert decision.strength > 0


def test_hold_when_not_enough_history() -> None:
    strategy = MovingAverageCrossoverStrategy(StrategyConfig(short_window=3, long_window=5))

    decision = strategy.decide("SPY", [10, 11])

    assert decision.signal is Signal.HOLD
