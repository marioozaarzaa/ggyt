from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from ggyt_bot.broker import Broker, SimulatedBroker
from ggyt_bot.data.feature_engine import build_features
from ggyt_bot.data.market_data import OHLCVSeries
from ggyt_bot.data.market_regime import (
    MarketRegime,
    detect_market_regime,
    regime_position_multiplier,
)
from ggyt_bot.execution.execution_engine import ExecutionEngine
from ggyt_bot.jarvis.agents.advisor import FinancialAdvisorAgent
from ggyt_bot.jarvis.agents.crypto import CryptoAgent
from ggyt_bot.jarvis.agents.marketing import MarketingAgent
from ggyt_bot.jarvis.agents.programming import ProgrammingAgent
from ggyt_bot.jarvis.agents.research import ResearchAgent
from ggyt_bot.jarvis.agents.web import WebCreationAgent
from ggyt_bot.jarvis.orchestrator import JarvisOrchestrator
from ggyt_bot.models import Signal
from ggyt_bot.risk import RiskManager
from ggyt_bot.risk.circuit_breaker import CircuitBreaker
from ggyt_bot.settings import BotConfig
from ggyt_bot.state import BotState
from ggyt_bot.storage.database import TradingDatabase
from ggyt_bot.strategies import (
    STRATEGY_REGISTRY,
    MeanReversionStrategy,
    SMAStrategy,
    TrendStrategy,
)
from ggyt_bot.strategies.strategy_base import StrategyBase, StrategyContext


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
        self.strategy = _build_strategy(strategy_cls, config)
        self.risk = RiskManager(config)
        self.execution = ExecutionEngine(config.execution)
        self.circuit_breaker = CircuitBreaker(
            hard_drawdown_pct=max(config.risk.max_drawdown_pct, 0.10)
        )
        self.jarvis = None
        if config.jarvis.enabled and database:
            self.jarvis = JarvisOrchestrator(database)
            self.jarvis.personality = config.jarvis.personality
            self.jarvis.register_agent(FinancialAdvisorAgent())
            self.jarvis.register_agent(ProgrammingAgent())
            self.jarvis.register_agent(WebCreationAgent())
            self.jarvis.register_agent(MarketingAgent())
            self.jarvis.register_agent(CryptoAgent())
            self.jarvis.register_agent(ResearchAgent())

    def run_once(self) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []

        # Process pending approved actions from Jarvis
        if self.jarvis and self.database:
            self._process_jarvis_actions()

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
            regime = detect_market_regime(features)

            if self.jarvis:
                jarvis_context = {
                    "symbol": symbol,
                    "regime": regime.value,
                    "volatility": features.volatility20,
                    "equity": account.equity,
                    "ts": datetime.now(UTC).isoformat(),
                }
                jarvis_thought = self.jarvis.think(jarvis_context)
                events.append(
                    self._event(
                        "JARVIS_THOUGHT",
                        symbol=symbol,
                        thought=jarvis_thought,
                    )
                )

            events.append(
                self._event(
                    "MARKET_CONDITION",
                    symbol=symbol,
                    regime=regime.value,
                    volatility=features.volatility20,
                    spread=features.spread_pct,
                )
            )
            if regime is MarketRegime.PANIC:
                self.state.halt(f"panic market regime detected for {symbol}")
                self.broker.panic_flatten()
                events.append(self._event("HALT", symbol=symbol, reason=self.state.halt_reason))
                break
            strategy = self._strategy_for_regime(regime)
            context = StrategyContext(
                symbol=symbol,
                market_data=market_data,
                features=features,
                account_equity=account.equity,
                market_regime=regime,
            )
            decision = strategy.generate_signal(context)
            events.append(
                self._event(
                    "SIGNAL",
                    symbol=symbol,
                    signal=decision.signal.value,
                    strategy=getattr(strategy, "name", "unknown"),
                    confidence=round(decision.confidence, 6),
                    score=round(decision.score, 6),
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
                ) * regime_position_multiplier(regime)
                execution_decision = self.execution.validate_trade(
                    notional=notional,
                    features=features,
                )
                if isinstance(self.broker, SimulatedBroker):
                    execution_decision = execution_decision.__class__(
                        True,
                        "simulated broker bypasses wall-clock trading windows",
                        execution_decision.estimated_spread_pct,
                        execution_decision.estimated_slippage_pct,
                        [notional],
                    )
                if execution_decision.allowed and notional > 1:
                    for order_slice in execution_decision.order_slices:
                        self.broker.buy_notional(symbol, order_slice)
                    events.append(
                        self._event(
                            "BUY",
                            symbol=symbol,
                            notional=round(notional, 2),
                            slices=len(execution_decision.order_slices),
                        )
                    )
                else:
                    events.append(
                        self._event("SKIP_TRADE", symbol=symbol, reason=execution_decision.reason)
                    )
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

    def _strategy_for_regime(self, regime: MarketRegime) -> StrategyBase:
        if self.config.strategy_name not in {"sma", "multi_indicator_trend"}:
            return self.strategy
        if regime is MarketRegime.TRENDING:
            return TrendStrategy()
        if regime is MarketRegime.RANGING:
            return MeanReversionStrategy()
        return self.strategy

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
                "MARKET_CONDITION": "market_conditions",
                "SKIP_TRADE": "orders",
                "JARVIS_THOUGHT": "jarvis_memory",
            }.get(str(event.get("type")), "daily_stats")
            self.database.record(table, event)

    def _write_events(self, events: list[dict[str, object]]) -> None:
        if not events:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            for event in events:
                handle.write(json.dumps(event, sort_keys=True) + "\n")

    def _process_jarvis_actions(self) -> None:
        if not self.database or not self.jarvis:
            return
        # Check for approved actions in the database
        rows = self.database.latest("jarvis_memory", 50)
        for row in rows:
            if row.get("type") == "action" and row.get("status") == "approved":
                action_data = row.get("details", {})
                result = self.jarvis.execute_action(action_data.get("type"), action_data.get("params", {}))

                # Mark as executed
                new_payload = {**row, "status": "executed", "result": result}
                # Remove internal SQLite columns from payload
                new_payload.pop("id", None)
                new_payload.pop("created_at", None)

                self.database._conn.execute(
                    "UPDATE jarvis_memory SET payload = ? WHERE id = ?",
                    (json.dumps(new_payload, sort_keys=True), row["id"])
                )
                self.database._conn.commit()


def _build_strategy(strategy_cls: type[StrategyBase], config: BotConfig) -> StrategyBase:
    if strategy_cls is SMAStrategy:
        return strategy_cls(config.strategy)
    return strategy_cls()
