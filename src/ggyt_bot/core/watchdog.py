from __future__ import annotations

from dataclasses import dataclass

from ggyt_bot.models import AccountSnapshot
from ggyt_bot.state import BotState


@dataclass(frozen=True)
class WatchdogConfig:
    max_market_data_age_seconds: int = 60
    max_api_errors: int = 5
    minimum_equity: float = 0.0
    max_drawdown_pct: float = 0.005


class SafetyWatchdog:
    def __init__(self, config: WatchdogConfig) -> None:
        self.config = config
        self.api_errors = 0

    def record_api_error(self) -> None:
        self.api_errors += 1

    def reset_api_errors(self) -> None:
        self.api_errors = 0

    def evaluate(
        self,
        *,
        market_data_age_seconds: float,
        account: AccountSnapshot,
        state: BotState,
    ) -> str | None:
        if market_data_age_seconds > self.config.max_market_data_age_seconds:
            return f"market data stale ({market_data_age_seconds:.1f}s)"
        if self.api_errors > self.config.max_api_errors:
            return f"api error limit exceeded ({self.api_errors})"
        if account.equity < self.config.minimum_equity:
            return f"account equity below minimum ({account.equity:.2f})"
        if state.high_watermark_equity:
            drawdown = (state.high_watermark_equity - account.equity) / state.high_watermark_equity
            if drawdown > self.config.max_drawdown_pct:
                return f"watchdog drawdown limit exceeded ({drawdown:.4%})"
        return None
