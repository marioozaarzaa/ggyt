from __future__ import annotations

from dataclasses import dataclass

from ggyt_bot.broker import Broker
from ggyt_bot.storage.database import TradingDatabase


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    notional: float | None = None
    reason: str = ""


class OrderManager:
    def __init__(self, broker: Broker, database: TradingDatabase | None = None) -> None:
        self.broker = broker
        self.database = database

    def execute(self, intent: OrderIntent) -> None:
        if self.database:
            self.database.record("orders", intent.__dict__)
        if intent.side == "BUY" and intent.notional and intent.notional > 0:
            self.broker.buy_notional(intent.symbol, intent.notional)
        elif intent.side == "SELL":
            self.broker.close_position(intent.symbol)
        elif intent.side == "FLATTEN_ALL":
            self.broker.panic_flatten()
