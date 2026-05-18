from __future__ import annotations

from typing import Any

from ggyt_bot.broker import SimulatedBroker
from ggyt_bot.execution.broker_base import BrokerBase


class PaperBroker(SimulatedBroker, BrokerBase):
    """BrokerBase-compatible local paper/simulation broker."""

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        return None

    def is_connected(self) -> bool:
        return True

    def get_balance(self) -> float:
        return self.account().cash

    def get_equity(self) -> float:
        return self.account().equity

    def get_positions(self) -> list[Any]:
        return self.positions()

    def get_orders(self) -> list[Any]:
        return []

    def get_market_data(self, symbol: str, *args: Any, **kwargs: Any) -> list[float]:
        limit = int(kwargs.get("limit", args[0] if args else 100))
        return self.historical_closes(symbol, limit)

    def submit_order(self, order: dict[str, Any]) -> Any:
        side = str(order.get("side", "BUY")).upper()
        symbol = str(order["symbol"])
        if side == "BUY":
            self.buy_notional(symbol, float(order["notional"]))
        elif side == "SELL":
            self.close_position(symbol)
        return {"status": "filled", "broker": "PAPER", "order": order}

    def cancel_order(self, order_id: int | str) -> None:
        del order_id

    def sync(self) -> dict[str, Any]:
        return {
            "positions": [position.__dict__ for position in self.positions()],
            "orders": [],
            "balance": self.account().cash,
            "equity": self.account().equity,
        }

    def health_check(self) -> dict[str, Any]:
        return {"broker": "PAPER", "connected": True}


__all__ = ["PaperBroker", "SimulatedBroker"]
