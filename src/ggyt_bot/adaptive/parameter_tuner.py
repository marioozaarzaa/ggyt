from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from ggyt_bot.storage.database import TradingDatabase


@dataclass(frozen=True)
class AdaptiveParameters:
    ema_fast: int = 20
    stop_multiplier: float = 2.0
    risk_multiplier: float = 1.0

    def validate(self) -> None:
        if not 10 <= self.ema_fast <= 30:
            raise ValueError("EMA_FAST must stay within 10-30")
        if not 1 <= self.stop_multiplier <= 4:
            raise ValueError("STOP_MULTIPLIER must stay within 1-4")
        if not 0.5 <= self.risk_multiplier <= 2:
            raise ValueError("RISK_MULTIPLIER must stay within 0.5-2")


class LimitedAdaptiveTuner:
    """Bounded parameter updates only; never changes strategy logic autonomously."""

    def __init__(self, database: TradingDatabase | None = None) -> None:
        self.database = database
        self.parameters = AdaptiveParameters()

    def propose(self, *, win_rate: float, max_drawdown: float) -> AdaptiveParameters:
        ema_fast = self.parameters.ema_fast
        stop_multiplier = self.parameters.stop_multiplier
        risk_multiplier = self.parameters.risk_multiplier
        if max_drawdown > 0.05:
            risk_multiplier = max(0.5, risk_multiplier * 0.9)
            stop_multiplier = min(4.0, stop_multiplier * 1.1)
        elif win_rate > 0.55 and max_drawdown < 0.02:
            risk_multiplier = min(2.0, risk_multiplier * 1.05)
        proposed = AdaptiveParameters(ema_fast, stop_multiplier, risk_multiplier)
        proposed.validate()
        return proposed

    def apply_with_audit(self, proposed: AdaptiveParameters, reason: str) -> AdaptiveParameters:
        proposed.validate()
        previous = self.parameters
        self.parameters = proposed
        if self.database:
            self.database.record(
                "adaptive_adjustments",
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "previous": previous.__dict__,
                    "new": proposed.__dict__,
                    "reason": reason,
                },
            )
        return self.parameters
