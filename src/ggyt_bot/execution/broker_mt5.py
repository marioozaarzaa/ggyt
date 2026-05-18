from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from ggyt_bot.broker import Broker
from ggyt_bot.execution.broker_base import BrokerBase
from ggyt_bot.models import AccountSnapshot, PositionSnapshot
from ggyt_bot.security.policy import SecurityError
from ggyt_bot.settings import RuntimeSettings
from ggyt_bot.storage.database import TradingDatabase


@dataclass(frozen=True)
class MT5LotSize:
    symbol: str
    lots: float
    risk_amount: float
    stop_distance: float
    tick_value: float
    tick_size: float


class MT5Broker(Broker, BrokerBase):
    """Local-only MetaTrader 5 broker adapter.

    The MetaTrader5 package talks to the locally installed terminal. No remote control surface,
    webhook, public socket, or distributed execution worker is introduced here.
    """

    RECONNECT_BACKOFF_SECONDS = (1, 2, 5, 10, 30)

    def __init__(
        self,
        settings: RuntimeSettings,
        *,
        mt5_module: Any | None = None,
        database: TradingDatabase | None = None,
        audit_log_path: Path | None = None,
    ) -> None:
        settings.validate_local_only()
        self.settings = settings
        self.mt5 = mt5_module
        self.database = database
        self.audit_log_path = audit_log_path or settings.ggyt_log_path
        self.account_info: Any | None = None
        self._connected = False

    def connect(self) -> None:
        self.mt5 = self.mt5 or _load_mt5()
        kwargs: dict[str, Any] = {"timeout": self.settings.mt5_timeout}
        if self.settings.mt5_terminal_path:
            kwargs["path"] = self.settings.mt5_terminal_path
        if self.settings.mt5_login:
            kwargs["login"] = int(self.settings.mt5_login)
        if self.settings.mt5_password:
            kwargs["password"] = self.settings.mt5_password
        if self.settings.mt5_server:
            kwargs["server"] = self.settings.mt5_server
        connected = self.mt5.initialize(**kwargs)
        if not connected:
            error = self.mt5.last_error()
            self._record("errors", "MT5_CONNECT_FAILED", {"error": str(error)})
            raise ConnectionError(error)
        self._connected = True
        self.account_info = self.mt5.account_info()
        if self.account_info is None:
            self._record("errors", "MT5_ACCOUNT_INFO_MISSING", {})
            raise ConnectionError("MT5 account_info() returned None")
        self._validate_account_security(self.account_info)
        self._validate_terminal_permissions()
        for symbol in self.settings.mt5_allowed_symbols:
            self._ensure_symbol(symbol)
        self._record(
            "daily_stats",
            "MT5_CONNECTED",
            {
                "login": getattr(self.account_info, "login", None),
                "server": getattr(self.account_info, "server", self.settings.mt5_server),
                "allowed_symbols": self.settings.mt5_allowed_symbols,
            },
        )

    def disconnect(self) -> None:
        if self.mt5 is not None:
            self.mt5.shutdown()
        self._connected = False
        self._record("daily_stats", "MT5_DISCONNECTED", {})

    def is_connected(self) -> bool:
        if not self._connected or self.mt5 is None:
            return False
        try:
            return self.mt5.terminal_info() is not None and self.mt5.account_info() is not None
        except Exception:
            return False

    def reconnect(self) -> None:
        last_error: Exception | None = None
        for delay in self.RECONNECT_BACKOFF_SECONDS:
            try:
                self.disconnect()
                self.connect()
                self._record("daily_stats", "MT5_RECONNECTED", {"delay": delay})
                return
            except Exception as exc:  # pragma: no cover - defensive logging path
                last_error = exc
                self._record("errors", "MT5_RECONNECT_FAILED", {"delay": delay, "error": str(exc)})
                time.sleep(delay)
        raise ConnectionError(f"MT5 reconnect failed: {last_error}")

    def _ensure_connected(self) -> None:
        if not self.is_connected():
            if self.settings.mt5_auto_reconnect:
                self.reconnect()
            else:
                raise ConnectionError("MT5 connection is not active")

    def get_balance(self) -> float:
        self._ensure_connected()
        return float(self.mt5.account_info().balance)

    def get_equity(self) -> float:
        self._ensure_connected()
        return float(self.mt5.account_info().equity)

    def get_positions(self) -> list[Any]:
        self._ensure_connected()
        return list(self.mt5.positions_get() or [])

    def get_orders(self) -> list[Any]:
        self._ensure_connected()
        return list(self.mt5.orders_get() or [])

    def get_symbol_info(self, symbol: str) -> Any:
        self._ensure_connected()
        self._ensure_symbol(symbol)
        info = self.mt5.symbol_info(symbol)
        if info is None:
            raise ValueError(f"MT5 symbol info not available for {symbol}")
        return info

    def get_tick(self, symbol: str) -> Any:
        self._ensure_connected()
        self._ensure_symbol(symbol)
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            self._record("errors", "MT5_NO_TICK", {"symbol": symbol})
            raise ValueError(f"No MT5 tick data for {symbol}")
        return tick

    def get_spread(self, symbol: str) -> float:
        tick = self.get_tick(symbol)
        bid = float(getattr(tick, "bid", 0.0))
        ask = float(getattr(tick, "ask", 0.0))
        midpoint = (bid + ask) / 2 if bid and ask else 0.0
        return (ask - bid) / midpoint if midpoint else float("inf")

    def get_volume(self, symbol: str) -> float:
        tick = self.get_tick(symbol)
        return float(getattr(tick, "volume", getattr(tick, "volume_real", 0.0)) or 0.0)

    def get_market_status(self, symbol: str) -> dict[str, Any]:
        info = self.get_symbol_info(symbol)
        tick = self.get_tick(symbol)
        return {
            "symbol": symbol,
            "visible": bool(getattr(info, "visible", False)),
            "trade_mode": getattr(info, "trade_mode", None),
            "spread": self.get_spread(symbol),
            "has_tick": tick is not None,
        }

    def get_market_data(
        self, symbol: str, timeframe: str = "TIMEFRAME_M1", count: int = 100
    ) -> Any:
        self._ensure_connected()
        self._ensure_symbol(symbol)
        timeframe_value = getattr(self.mt5, timeframe, getattr(self.mt5, "TIMEFRAME_M1", 1))
        rates = self.mt5.copy_rates_from_pos(symbol, timeframe_value, 0, count)
        if rates is None or len(rates) == 0:
            self._record("errors", "MT5_NO_MARKET_DATA", {"symbol": symbol})
            raise ValueError(f"No MT5 OHLCV data for {symbol}")
        return rates

    def historical_closes(self, symbol: str, limit: int) -> list[float]:
        rates = self.get_market_data(symbol, count=limit)
        closes: list[float] = []
        for rate in rates:
            if isinstance(rate, dict):
                closes.append(float(rate["close"]))
            else:
                closes.append(float(rate.close if hasattr(rate, "close") else rate[4]))
        return closes[-limit:]

    def account(self) -> AccountSnapshot:
        self._ensure_connected()
        account = self.mt5.account_info()
        return AccountSnapshot(
            equity=float(account.equity),
            cash=float(account.balance),
            buying_power=float(getattr(account, "margin_free", account.equity)),
        )

    def positions(self) -> list[PositionSnapshot]:
        snapshots: list[PositionSnapshot] = []
        for position in self.get_positions():
            symbol = str(position.symbol)
            price_current = float(
                getattr(position, "price_current", getattr(position, "price_open", 0))
            )
            volume = float(position.volume)
            market_value = abs(volume * price_current)
            snapshots.append(
                PositionSnapshot(
                    symbol=symbol,
                    market_value=market_value,
                    unrealized_pl=float(getattr(position, "profit", 0.0)),
                    qty=volume,
                    avg_entry_price=float(getattr(position, "price_open", 0.0)),
                    current_price=price_current,
                )
            )
        return snapshots

    def calculate_lot_size(
        self,
        *,
        equity: float,
        risk_percent: float,
        stop_distance: float,
        symbol: str,
    ) -> MT5LotSize:
        info = self.get_symbol_info(symbol)
        tick_value = float(getattr(info, "trade_tick_value", 1.0) or 1.0)
        tick_size = float(
            getattr(info, "trade_tick_size", getattr(info, "point", 0.0001)) or 0.0001
        )
        min_lot = float(getattr(info, "volume_min", 0.01) or 0.01)
        max_lot = float(getattr(info, "volume_max", 100.0) or 100.0)
        lot_step = float(getattr(info, "volume_step", 0.01) or 0.01)
        risk_amount = equity * risk_percent
        ticks_at_risk = max(stop_distance / tick_size, 1e-9)
        raw_lots = risk_amount / (ticks_at_risk * tick_value)
        normalized = math.floor(raw_lots / lot_step) * lot_step
        lots = min(max(normalized, min_lot), max_lot)
        return MT5LotSize(symbol, round(lots, 8), risk_amount, stop_distance, tick_value, tick_size)

    def buy_notional(self, symbol: str, notional: float) -> None:
        tick = self.get_tick(symbol)
        price = float(tick.ask)
        lot_info = self.calculate_lot_size(
            equity=self.get_equity(),
            risk_percent=self.settings.mt5_default_risk_percent,
            stop_distance=max(
                price * 0.002, float(getattr(self.get_symbol_info(symbol), "point", 0.0001))
            ),
            symbol=symbol,
        )
        self.submit_order({"symbol": symbol, "side": "BUY", "volume": lot_info.lots})

    def submit_order(self, order: dict[str, Any]) -> Any:
        self._ensure_connected()
        symbol = str(order["symbol"]).upper()
        self._ensure_symbol(symbol)
        if not self.settings.ggyt_allow_live_trading or self.settings.ggyt_dry_run:
            self._record("orders", "MT5_DRY_RUN_ORDER", {"order": order})
            return SimpleNamespace(retcode=0, comment="dry-run", request=order)
        self._validate_account_security(self.mt5.account_info())
        spread = self.get_spread(symbol)
        if spread > self.settings.mt5_max_spread_pct:
            self._record("orders", "MT5_ORDER_REJECTED", {"symbol": symbol, "spread": spread})
            raise ValueError(
                f"MT5 spread {spread:.6f} exceeds max {self.settings.mt5_max_spread_pct}"
            )
        if not self.get_market_status(symbol)["has_tick"]:
            raise ValueError(f"MT5 market has no data for {symbol}")
        request = self._build_order_request(order)
        last_result = None
        for filling in self._filling_modes():
            request["type_filling"] = filling
            result = self.mt5.order_send(request)
            last_result = result
            retcode = getattr(result, "retcode", None)
            if retcode in self._success_retcodes():
                self._record(
                    "orders",
                    "MT5_ORDER_FILLED",
                    {"request": request, "retcode": retcode, "spread": spread},
                )
                return result
        self._record(
            "errors",
            "MT5_ORDER_FAILED",
            {"request": request, "result": str(last_result), "spread": spread},
        )
        raise RuntimeError(f"MT5 order failed: {last_result}")

    def close_position(self, symbol: str) -> None:
        self._ensure_connected()
        positions = [
            item for item in self.get_positions() if str(item.symbol).upper() == symbol.upper()
        ]
        for position in positions:
            tick = self.get_tick(position.symbol)
            position_type = getattr(position, "type", getattr(self.mt5, "POSITION_TYPE_BUY", 0))
            is_buy = position_type == getattr(self.mt5, "POSITION_TYPE_BUY", 0)
            order_type = getattr(self.mt5, "ORDER_TYPE_SELL" if is_buy else "ORDER_TYPE_BUY")
            price = float(tick.bid if is_buy else tick.ask)
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": float(position.volume),
                "type": order_type,
                "position": getattr(position, "ticket", 0),
                "price": price,
                "deviation": self.settings.mt5_max_slippage,
                "magic": self.settings.mt5_magic_number,
                "comment": "GGYT BOT CLOSE",
                "type_time": self.mt5.ORDER_TIME_GTC,
            }
            if self.settings.ggyt_dry_run:
                self._record("orders", "MT5_DRY_RUN_CLOSE", request)
            else:
                self.mt5.order_send(request)
                self._record("orders", "MT5_CLOSE_SENT", request)

    def cancel_order(self, order_id: int | str) -> None:
        self._ensure_connected()
        request = {"action": self.mt5.TRADE_ACTION_REMOVE, "order": int(order_id)}
        if self.settings.ggyt_dry_run:
            self._record("orders", "MT5_DRY_RUN_CANCEL", request)
            return
        result = self.mt5.order_send(request)
        self._record("orders", "MT5_CANCEL_SENT", {"order_id": order_id, "result": str(result)})

    def panic_flatten(self) -> None:
        for position in self.get_positions():
            self.close_position(str(position.symbol))

    def sync(self) -> dict[str, Any]:
        self._ensure_connected()
        payload = {
            "positions": [
                vars(item) if hasattr(item, "__dict__") else str(item)
                for item in self.get_positions()
            ],
            "orders": [
                vars(item) if hasattr(item, "__dict__") else str(item)
                for item in self.get_orders()
            ],
            "balance": self.get_balance(),
            "equity": self.get_equity(),
        }
        self._record("daily_stats", "MT5_SYNC", payload)
        return payload

    def health_check(self) -> dict[str, Any]:
        connected = self.is_connected()
        status = {"connected": connected, "broker": "MT5"}
        if not connected:
            if self.settings.mt5_auto_reconnect:
                try:
                    self.reconnect()
                    status["reconnected"] = True
                except Exception as exc:
                    status["error"] = str(exc)
                    status["stop_engine"] = True
            return status
        account = self.mt5.account_info()
        terminal = self.mt5.terminal_info()
        status.update(
            {
                "login": getattr(account, "login", None),
                "trade_allowed": bool(getattr(account, "trade_allowed", True))
                and bool(getattr(terminal, "trade_allowed", True)),
                "equity": getattr(account, "equity", None),
            }
        )
        if not status["trade_allowed"]:
            status["stop_engine"] = True
        return status

    def update_atr_trailing_stop(self, symbol: str, atr: float, multiplier: float = 2.0) -> None:
        self._ensure_connected()
        stop_distance = atr * multiplier
        for position in self.get_positions():
            if str(position.symbol).upper() != symbol.upper():
                continue
            is_buy = getattr(position, "type", 0) == getattr(self.mt5, "POSITION_TYPE_BUY", 0)
            current = float(
                getattr(position, "price_current", getattr(position, "price_open", 0.0))
            )
            new_sl = current - stop_distance if is_buy else current + stop_distance
            request = {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "position": getattr(position, "ticket", 0),
                "symbol": position.symbol,
                "sl": new_sl,
                "tp": getattr(position, "tp", 0.0),
                "magic": self.settings.mt5_magic_number,
                "comment": "GGYT BOT ATR TRAIL",
            }
            if self.settings.ggyt_dry_run:
                self._record("orders", "MT5_DRY_RUN_TRAILING_STOP", request)
            else:
                self.mt5.order_send(request)
                self._record("orders", "MT5_TRAILING_STOP_SENT", request)

    def _build_order_request(self, order: dict[str, Any]) -> dict[str, Any]:
        symbol = str(order["symbol"]).upper()
        side = str(order.get("side", "BUY")).upper()
        order_kind = str(order.get("order_type", "MARKET")).upper()
        tick = self.get_tick(symbol)
        action = self.mt5.TRADE_ACTION_DEAL
        type_name = (
            f"ORDER_TYPE_{side}"
            if order_kind == "MARKET"
            else f"ORDER_TYPE_{side}_{order_kind}"
        )
        order_type = getattr(self.mt5, type_name)
        if order_kind != "MARKET":
            action = self.mt5.TRADE_ACTION_PENDING
        price = float(order.get("price") or (tick.ask if side == "BUY" else tick.bid))
        request = {
            "action": action,
            "symbol": symbol,
            "volume": float(order["volume"]),
            "price": price,
            "type": order_type,
            "deviation": int(order.get("deviation", self.settings.mt5_max_slippage)),
            "magic": self.settings.mt5_magic_number,
            "comment": str(order.get("comment", "GGYT BOT")),
            "type_time": self.mt5.ORDER_TIME_GTC,
        }
        if "sl" in order:
            request["sl"] = float(order["sl"])
        if "tp" in order:
            request["tp"] = float(order["tp"])
        return request

    def _ensure_symbol(self, symbol: str) -> None:
        normalized = symbol.upper()
        if normalized not in self.settings.mt5_allowed_symbols:
            self._record("orders", "MT5_SYMBOL_REJECTED", {"symbol": normalized})
            raise ValueError(f"MT5 symbol {normalized} is not in MT5_ALLOWED_SYMBOLS")
        info = self.mt5.symbol_info(normalized)
        if info is None:
            raise ValueError(f"MT5 symbol {normalized} is unavailable")
        if not bool(getattr(info, "visible", False)) and not self.mt5.symbol_select(
            normalized, True
        ):
            raise ValueError(f"Could not activate MT5 symbol {normalized}")

    def _validate_account_security(self, account_info: Any) -> None:
        login = str(getattr(account_info, "login", ""))
        if not self.settings.ggyt_dry_run:
            if not self.settings.ggyt_allow_live_trading:
                raise SecurityError("MT5 live order routing requires GGYT_ALLOW_LIVE_TRADING=true")
            if login != self.settings.ggyt_confirm_mt5_account:
                raise SecurityError("MT5 account login does not match GGYT_CONFIRM_MT5_ACCOUNT")

    def _validate_terminal_permissions(self) -> None:
        terminal = self.mt5.terminal_info()
        account = self.mt5.account_info()
        if not bool(getattr(terminal, "trade_allowed", True)):
            raise PermissionError("MT5 terminal trading is disabled")
        if not bool(getattr(account, "trade_allowed", True)):
            raise PermissionError("MT5 account trading is disabled")

    def _filling_modes(self) -> list[int]:
        return [
            self.mt5.ORDER_FILLING_RETURN,
            self.mt5.ORDER_FILLING_IOC,
            self.mt5.ORDER_FILLING_FOK,
        ]

    def _success_retcodes(self) -> set[int]:
        return {
            getattr(self.mt5, "TRADE_RETCODE_DONE", 10009),
            getattr(self.mt5, "TRADE_RETCODE_PLACED", 10008),
        }

    def _record(self, table: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {"ts": datetime.now(UTC).isoformat(), "type": event_type, **payload}
        if self.database:
            self.database.record(table, event)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")


def _load_mt5() -> Any:
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "MetaTrader5 is required for MT5 execution. Install dependencies and run locally."
        ) from exc
    return mt5
