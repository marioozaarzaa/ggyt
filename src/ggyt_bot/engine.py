from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from ggyt_bot.broker import Broker
from ggyt_bot.data.feature_engine import build_features
from ggyt_bot.data.market_data import OHLCVSeries
from ggyt_bot.models import Signal
from ggyt_bot.risk import RiskManager
from ggyt_bot.settings import BotConfig
from ggyt_bot.state import BotState
from ggyt_bot.storage.database import TradingDatabase
from ggyt_bot.strategies import STRATEGY_REGISTRY, SMAStrategy
from ggyt_bot.strategies.strategy_base import StrategyContext


class TradingEngine:
    def __init__(
        self,
        broker: Broker,
        config: BotConfig,
        state: BotState,
        log_path: Path,
        database: TradingDatabase | None = None,
    ) -> None:
        self.broker = broker
        self.config = config
        self.state = state
        self.log_path = log_path
        self.database = database
        strategy_cls = STRATEGY_REGISTRY.get(config.strategy_name, SMAStrategy)
        self.strategy = (
            strategy_cls(config.strategy) if strategy_cls is SMAStrategy else strategy_cls()
        )
        self.risk = RiskManager(config)

    def run_once(self) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        account = self.broker.account()
        positions = self.broker.positions()
        halt_reason = self.risk.halt_reason(account, positions, self.state)
        if halt_reason:
            self.state.halt(halt_reason)
            events.append(self._event("HALT", reason=halt_reason, equity=account.equity))
            if self.config.risk.liquidate_on_halt:
                self.broker.panic_flatten()
                events.append(self._event("PANIC_FLATTEN", reason=halt_reason))
            self._persist_events(events)
            return events

        held_symbols = {position.symbol for position in positions if position.qty > 0}
        history_limit = max(self.config.strategy.long_window, 220)
        for symbol in self.config.symbols:
            closes = self.broker.historical_closes(symbol, history_limit)
            market_data = OHLCVSeries.from_closes(symbol, closes)
            features = build_features(market_data)
            context = StrategyContext(symbol=symbol, market_data=market_data, features=features)
            decision = self.strategy.generate_signal(context)
            events.append(
                self._event(
                    "SIGNAL",
                    symbol=symbol,
                    signal=decision.signal.value,
                    strategy=getattr(self.strategy, "name", "unknown"),
                    strength=round(decision.strength, 6),
                    reason=decision.reason,
                )
            )
            if decision.signal is Signal.BUY and symbol not in held_symbols:
                notional = self.risk.allowed_notional(
                    account,
                    positions,
                    decision,
                    atr=features.atr14,
                    price=features.last_close,
                )
                if notional > 1:
                    self.broker.buy_notional(symbol, notional)
                    events.append(self._event("BUY", symbol=symbol, notional=round(notional, 2)))
            elif decision.signal is Signal.SELL and symbol in held_symbols:
                self.broker.close_position(symbol)
                events.append(self._event("CLOSE", symbol=symbol, reason=decision.reason))

        self._persist_events(events)
        return events

    def run_forever(self) -> None:
        while True:
            self.run_once()
            if self.state.halted:
                return
            time.sleep(self.config.execution.poll_seconds)

    def _event(self, event_type: str, **payload: object) -> dict[str, object]:
        return {"ts": datetime.now(UTC).isoformat(), "type": event_type, **payload}

    def _persist_events(self, events: list[dict[str, object]]) -> None:
        self._write_events(events)
        if not self.database:
            return
        for event in events:
            table = {
                "SIGNAL": "signals",
                "BUY": "orders",
                "CLOSE": "orders",
                "HALT": "errors",
                "PANIC_FLATTEN": "orders",
            }.get(str(event.get("type")), "daily_stats")
            self.database.record(table, event)

    def _write_events(self, events: list[dict[str, object]]) -> None:
        if not events:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True) + "\n")
