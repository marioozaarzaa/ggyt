from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from typing import Any

from ggyt_bot.models import AccountSnapshot, PositionSnapshot
from ggyt_bot.settings import RuntimeSettings


class Broker(ABC):
    @abstractmethod
    def account(self) -> AccountSnapshot: ...

    @abstractmethod
    def positions(self) -> list[PositionSnapshot]: ...

    @abstractmethod
    def historical_closes(self, symbol: str, limit: int) -> list[float]: ...

    @abstractmethod
    def buy_notional(self, symbol: str, notional: float) -> None: ...

    @abstractmethod
    def close_position(self, symbol: str) -> None: ...

    @abstractmethod
    def panic_flatten(self) -> None: ...


class AlpacaBroker(Broker):
    def __init__(self, settings: RuntimeSettings) -> None:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.trading.client import TradingClient
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "alpaca-py is required for Alpaca execution. Run: pip install -e ."
            ) from exc

        settings.validate_execution_safety()
        self.settings = settings
        self.trading = TradingClient(
            api_key=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            paper=settings.alpaca_paper,
        )
        self.data = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)
        if not settings.alpaca_paper:
            account = self.trading.get_account()
            account_id = str(getattr(account, "id", ""))
            if account_id != settings.ggyt_confirm_live_account_id:
                from ggyt_bot.security.policy import SecurityError

                raise SecurityError(
                    "Live Alpaca account id does not match GGYT_CONFIRM_LIVE_ACCOUNT_ID"
                )

    def account(self) -> AccountSnapshot:
        account = self.trading.get_account()
        return AccountSnapshot(
            equity=float(account.equity),
            cash=float(account.cash),
            buying_power=float(account.buying_power),
        )

    def positions(self) -> list[PositionSnapshot]:
        return [
            PositionSnapshot(
                symbol=str(position.symbol),
                market_value=float(position.market_value),
                unrealized_pl=float(position.unrealized_pl),
                qty=float(position.qty),
                avg_entry_price=float(position.avg_entry_price),
                current_price=float(position.current_price),
            )
            for position in self.trading.get_all_positions()
        ]

    def historical_closes(self, symbol: str, limit: int) -> list[float]:
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.now(UTC) - timedelta(days=max(90, limit * 3)),
            end=datetime.now(UTC),
            limit=limit,
        )
        bars = self.data.get_stock_bars(request).data.get(symbol, [])
        return [float(bar.close) for bar in bars][-limit:]

    def buy_notional(self, symbol: str, notional: float) -> None:
        if self.settings.ggyt_dry_run:
            return
        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        self.trading.submit_order(
            MarketOrderRequest(
                symbol=symbol,
                notional=round(notional, 2),
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
        )

    def close_position(self, symbol: str) -> None:
        if self.settings.ggyt_dry_run:
            return
        self.trading.close_position(symbol)

    def panic_flatten(self) -> None:
        if self.settings.ggyt_dry_run:
            return
        self.trading.cancel_orders()
        self.trading.close_all_positions(cancel_orders=True)


class SimulatedBroker(Broker):
    """Deterministic broker for tests and dry local demos; never touches a real account."""

    def __init__(self, prices: dict[str, list[float]], equity: float = 100_000.0) -> None:
        self.prices = prices
        self.cash = equity
        self._positions: dict[str, dict[str, Any]] = {}

    def account(self) -> AccountSnapshot:
        equity = self.cash + sum(
            position["qty"] * self.prices[symbol][-1]
            for symbol, position in self._positions.items()
        )
        return AccountSnapshot(equity=equity, cash=self.cash, buying_power=self.cash)

    def positions(self) -> list[PositionSnapshot]:
        snapshots: list[PositionSnapshot] = []
        for symbol, position in self._positions.items():
            current_price = self.prices[symbol][-1]
            market_value = position["qty"] * current_price
            unrealized = market_value - position["qty"] * position["avg_entry_price"]
            snapshots.append(
                PositionSnapshot(
                    symbol,
                    market_value,
                    unrealized,
                    position["qty"],
                    position["avg_entry_price"],
                    current_price,
                )
            )
        return snapshots

    def historical_closes(self, symbol: str, limit: int) -> list[float]:
        return self.prices[symbol][-limit:]

    def buy_notional(self, symbol: str, notional: float) -> None:
        price = self.prices[symbol][-1]
        qty = notional / price
        self.cash -= notional
        self._positions[symbol] = {"qty": qty, "avg_entry_price": price}

    def close_position(self, symbol: str) -> None:
        position = self._positions.pop(symbol, None)
        if position:
            self.cash += position["qty"] * self.prices[symbol][-1]

    def panic_flatten(self) -> None:
        for symbol in list(self._positions):
            self.close_position(symbol)
