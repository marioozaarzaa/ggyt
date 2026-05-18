from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BrokerBase(ABC):
    """Common broker contract for local execution adapters."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def get_balance(self) -> float: ...

    @abstractmethod
    def get_equity(self) -> float: ...

    @abstractmethod
    def get_positions(self) -> list[Any]: ...

    @abstractmethod
    def get_orders(self) -> list[Any]: ...

    @abstractmethod
    def get_market_data(self, symbol: str, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    def submit_order(self, order: dict[str, Any]) -> Any: ...

    @abstractmethod
    def close_position(self, symbol: str) -> None: ...

    @abstractmethod
    def cancel_order(self, order_id: int | str) -> None: ...

    @abstractmethod
    def sync(self) -> dict[str, Any]: ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]: ...
