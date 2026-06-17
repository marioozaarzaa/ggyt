from pathlib import Path

from ggyt_bot.broker import SimulatedBroker
from ggyt_bot.engine import TradingEngine
from ggyt_bot.storage.database import TradingDatabase
from ggyt_bot.settings import BotConfig, ExecutionConfig, RiskConfig, StrategyConfig
from ggyt_bot.state import BotState


def test_engine_buys_in_simulation_when_signal_is_positive(tmp_path: Path) -> None:
    config = BotConfig(
        symbols=["SPY"],
        strategy=StrategyConfig(short_window=3, long_window=5, min_signal_strength=0.001),
        risk=RiskConfig(stop_on_any_loss=False),
        execution=ExecutionConfig(min_cash_reserve_pct=0.5),
    )
    broker = SimulatedBroker({"SPY": [10, 10, 10, 11, 12]})
    db = TradingDatabase(tmp_path / "test.db")
    engine = TradingEngine(broker, config, BotState(), tmp_path / "events.jsonl", database=db)

    events = engine.run_once()

    assert any(event["type"] == "JARVIS_THOUGHT" for event in events)
    assert any(event["type"] == "BUY" for event in events)
    assert broker.positions()
