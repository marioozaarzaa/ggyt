from __future__ import annotations

from pathlib import Path

from ggyt_bot.broker import Broker
from ggyt_bot.state import BotState
from ggyt_bot.storage.database import TradingDatabase


class StateManager:
    def __init__(self, path: Path, broker: Broker, database: TradingDatabase | None = None) -> None:
        self.path = path
        self.broker = broker
        self.database = database
        self.state = BotState.load(path)

    def startup(self) -> BotState:
        self.load_state()
        self.sync_positions()
        self.sync_orders()
        self.recover_open_positions()
        self.resume_engine()
        self.state.save(self.path)
        return self.state

    def load_state(self) -> BotState:
        self.state = BotState.load(self.path)
        return self.state

    def sync_positions(self) -> None:
        positions = self.broker.positions()
        self.state.positions_synced = True
        if self.database:
            for position in positions:
                self.database.record("positions", position.__dict__)

    def sync_orders(self) -> None:
        self.state.open_orders_synced = True
        if self.database:
            self.database.record(
                "orders", {"event": "sync_orders", "status": "not_supported_by_broker"}
            )

    def recover_open_positions(self) -> None:
        if self.database:
            self.database.record("daily_stats", {"event": "recover_open_positions"})

    def resume_engine(self) -> None:
        if not self.state.kill_switch_enabled:
            self.state.halted = False
            self.state.halt_reason = None
