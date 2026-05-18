from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class CircuitBreakerState:
    consecutive_losses: int = 0
    stopped_until: datetime | None = None
    emergency_mode: bool = False
    stop_engine: bool = False
    reason: str | None = None


class CircuitBreaker:
    def __init__(
        self,
        *,
        max_consecutive_losses: int = 3,
        hard_drawdown_pct: float = 0.10,
        high_volatility_threshold: float = 0.45,
    ) -> None:
        self.max_consecutive_losses = max_consecutive_losses
        self.hard_drawdown_pct = hard_drawdown_pct
        self.high_volatility_threshold = high_volatility_threshold
        self.state = CircuitBreakerState()

    def record_trade_result(self, pnl: float) -> None:
        self.state.consecutive_losses = self.state.consecutive_losses + 1 if pnl < 0 else 0
        if self.state.consecutive_losses >= self.max_consecutive_losses:
            self.stop_trading(hours=24, reason="consecutive loss circuit breaker")

    def evaluate(self, *, drawdown_pct: float, volatility: float | None) -> CircuitBreakerState:
        now = datetime.now(UTC)
        if self.state.stopped_until and now < self.state.stopped_until:
            return self.state
        if self.state.stopped_until and now >= self.state.stopped_until:
            self.state.stopped_until = None
            self.state.reason = None
        if drawdown_pct > self.hard_drawdown_pct:
            self.state.stop_engine = True
            self.state.reason = "hard drawdown circuit breaker"
        if volatility is not None and volatility > self.high_volatility_threshold:
            self.emergency_mode("high volatility circuit breaker")
        return self.state

    def stop_trading(self, *, hours: int, reason: str) -> None:
        self.state.stopped_until = datetime.now(UTC) + timedelta(hours=hours)
        self.state.reason = reason

    def emergency_mode(self, reason: str) -> None:
        self.state.emergency_mode = True
        self.state.reason = reason
