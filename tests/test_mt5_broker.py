from types import SimpleNamespace

import pytest

from ggyt_bot.execution.broker_mt5 import MT5Broker
from ggyt_bot.security.policy import SecurityError
from ggyt_bot.settings import RuntimeSettings


class FakeMT5:
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_REMOVE = 6
    TRADE_ACTION_SLTP = 7
    ORDER_TYPE_BUY = 10
    ORDER_TYPE_SELL = 11
    ORDER_TYPE_BUY_LIMIT = 12
    ORDER_TYPE_SELL_LIMIT = 13
    ORDER_TYPE_BUY_STOP = 14
    ORDER_TYPE_SELL_STOP = 15
    ORDER_TIME_GTC = 20
    ORDER_FILLING_RETURN = 30
    ORDER_FILLING_IOC = 31
    ORDER_FILLING_FOK = 32
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    TIMEFRAME_M1 = 1

    def __init__(self) -> None:
        self.initialized = False
        self.selected: list[str] = []
        self.sent: list[dict] = []
        self.fail_initialize_times = 0

    def initialize(self, **kwargs):
        del kwargs
        if self.fail_initialize_times:
            self.fail_initialize_times -= 1
            return False
        self.initialized = True
        return True

    def shutdown(self):
        self.initialized = False

    def last_error(self):
        return (1, "fake error")

    def account_info(self):
        if not self.initialized:
            return None
        return SimpleNamespace(
            login=123456,
            balance=100_000.0,
            equity=101_000.0,
            margin_free=90_000.0,
            trade_allowed=True,
            server="Demo",
        )

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True) if self.initialized else None

    def symbol_info(self, symbol):
        if symbol not in {"EURUSD", "XAUUSD"}:
            return None
        return SimpleNamespace(
            name=symbol,
            visible=symbol in self.selected,
            volume_min=0.01,
            volume_max=100.0,
            volume_step=0.01,
            trade_tick_value=10.0,
            trade_tick_size=0.0001,
            point=0.0001,
            trade_mode=1,
        )

    def symbol_select(self, symbol, enabled):
        if enabled:
            self.selected.append(symbol)
        return True

    def symbol_info_tick(self, symbol):
        del symbol
        return SimpleNamespace(bid=1.1000, ask=1.1002, volume=1000)

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        del symbol, timeframe, start
        return [SimpleNamespace(close=1.0 + i * 0.001) for i in range(count)]

    def positions_get(self):
        return [
            SimpleNamespace(
                symbol="EURUSD",
                volume=0.1,
                price_open=1.09,
                price_current=1.10,
                profit=100.0,
                type=self.POSITION_TYPE_BUY,
                ticket=7,
                tp=0.0,
            )
        ]

    def orders_get(self):
        return [SimpleNamespace(ticket=99, symbol="EURUSD")]

    def order_send(self, request):
        self.sent.append(request.copy())
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment="done")


def _settings(**overrides) -> RuntimeSettings:
    defaults = dict(
        broker="MT5",
        ggyt_dry_run=True,
        mt5_login="123456",
        mt5_password="password",
        mt5_server="Demo",
        mt5_allowed_symbols=["EURUSD", "XAUUSD"],
        ggyt_confirm_mt5_account="123456",
    )
    defaults.update(overrides)
    return RuntimeSettings(**defaults)


def test_mt5_connect_activates_allowed_symbols(tmp_path) -> None:
    fake = FakeMT5()
    broker = MT5Broker(_settings(ggyt_log_path=tmp_path / "audit.jsonl"), mt5_module=fake)

    broker.connect()

    assert broker.is_connected()
    assert set(fake.selected) == {"EURUSD", "XAUUSD"}
    assert broker.get_balance() == 100_000.0
    assert broker.get_equity() == 101_000.0


def test_mt5_rejects_symbol_not_in_allowlist(tmp_path) -> None:
    broker = MT5Broker(_settings(ggyt_log_path=tmp_path / "audit.jsonl"), mt5_module=FakeMT5())
    broker.connect()

    with pytest.raises(ValueError, match="MT5_ALLOWED_SYMBOLS"):
        broker.get_tick("GBPUSD")


def test_mt5_lot_size_normalizes_to_step(tmp_path) -> None:
    broker = MT5Broker(_settings(ggyt_log_path=tmp_path / "audit.jsonl"), mt5_module=FakeMT5())
    broker.connect()

    lot = broker.calculate_lot_size(
        equity=100_000,
        risk_percent=0.005,
        stop_distance=0.005,
        symbol="EURUSD",
    )

    assert lot.lots == 1.0


def test_mt5_dry_run_submit_order_does_not_send(tmp_path) -> None:
    fake = FakeMT5()
    broker = MT5Broker(_settings(ggyt_log_path=tmp_path / "audit.jsonl"), mt5_module=fake)
    broker.connect()

    result = broker.submit_order({"symbol": "EURUSD", "side": "BUY", "volume": 0.1})

    assert result.comment == "dry-run"
    assert fake.sent == []


def test_mt5_live_requires_confirmed_account(tmp_path) -> None:
    broker = MT5Broker(
        _settings(
            ggyt_log_path=tmp_path / "audit.jsonl",
            ggyt_dry_run=False,
            ggyt_allow_live_trading=True,
            ggyt_confirm_mt5_account="999",
        ),
        mt5_module=FakeMT5(),
    )

    with pytest.raises(SecurityError):
        broker.connect()


def test_mt5_reconnect_uses_backoff(monkeypatch, tmp_path) -> None:
    fake = FakeMT5()
    fake.fail_initialize_times = 1
    sleeps: list[int] = []
    monkeypatch.setattr(
        "ggyt_bot.execution.broker_mt5.time.sleep", lambda delay: sleeps.append(delay)
    )
    broker = MT5Broker(_settings(ggyt_log_path=tmp_path / "audit.jsonl"), mt5_module=fake)

    broker.reconnect()

    assert broker.is_connected()
    assert sleeps == [1]
