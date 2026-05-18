from __future__ import annotations

from typing import Any

from ggyt_bot.broker import AlpacaBroker
from ggyt_bot.execution.broker_base import BrokerBase


class AlpacaBrokerAdapter(AlpacaBroker, BrokerBase):
    """BrokerBase-compatible adapter around the existing Alpaca broker."""

    def connect(self) -> None:
        self.settings.validate_execution_safety()

    def disconnect(self) -> None:
        return None

    def is_connected(self) -> bool:
        try:
            self.trading.get_account()
            return True
        except Exception:
            return False

    def get_balance(self) -> float:
        return self.account().cash

    def get_equity(self) -> float:
        return self.account().equity

    def get_positions(self) -> list[Any]:
        return self.positions()

    def get_orders(self) -> list[Any]:
        try:
            return list(self.trading.get_orders())
        except Exception:
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
        return {"status": "submitted", "broker": "ALPACA", "order": order}

    def cancel_order(self, order_id: int | str) -> None:
        if self.settings.ggyt_dry_run:
            return
        self.trading.cancel_order_by_id(str(order_id))

    def sync(self) -> dict[str, Any]:
        account = self.account()
        return {
            "positions": [position.__dict__ for position in self.positions()],
            "orders": self.get_orders(),
            "balance": account.cash,
            "equity": account.equity,
        }

    def health_check(self) -> dict[str, Any]:
        return {"broker": "ALPACA", "connected": self.is_connected()}


__all__ = ["AlpacaBroker", "AlpacaBrokerAdapter"]
