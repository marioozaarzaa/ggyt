from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from ggyt_bot.data.feature_engine import FeatureSet
from ggyt_bot.settings import ExecutionConfig


@dataclass(frozen=True)
class ExecutionDecision:
    allowed: bool
    reason: str
    estimated_spread_pct: float
    estimated_slippage_pct: float
    order_slices: list[float]


class ExecutionEngine:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def validate_trade(
        self,
        *,
        notional: float,
        features: FeatureSet,
        now: datetime | None = None,
    ) -> ExecutionDecision:
        spread = self.estimate_spread(features)
        slippage = self.estimate_slippage(notional=notional, features=features)
        if not self.in_trading_window(now or datetime.now()):
            return ExecutionDecision(
                False, "outside configured trading window", spread, slippage, []
            )
        if self.avoid_bad_liquidity(features):
            return ExecutionDecision(False, "bad liquidity conditions", spread, slippage, [])
        if spread > self.config.max_spread_pct:
            return ExecutionDecision(False, "spread exceeds max_spread_pct", spread, slippage, [])
        if slippage > self.config.max_slippage_pct:
            return ExecutionDecision(
                False, "slippage exceeds max_slippage_pct", spread, slippage, []
            )
        return ExecutionDecision(
            True, "execution checks passed", spread, slippage, self.split_orders(notional)
        )

    def estimate_spread(self, features: FeatureSet) -> float:
        return features.spread_pct if features.spread_pct is not None else 0.001

    def estimate_slippage(self, *, notional: float, features: FeatureSet) -> float:
        liquidity_penalty = 0.001 if (features.relative_volume20 or 1.0) < 1 else 0.0005
        size_penalty = min(0.002, notional / 1_000_000 * 0.001)
        volatility_penalty = min(0.003, (features.volatility20 or 0.10) * 0.002)
        return liquidity_penalty + size_penalty + volatility_penalty

    def avoid_bad_liquidity(self, features: FeatureSet) -> bool:
        return (features.relative_volume20 or 1.0) < 0.5

    def split_orders(self, notional: float, max_slice_notional: float = 10_000.0) -> list[float]:
        if notional <= max_slice_notional:
            return [notional]
        slices = int(notional // max_slice_notional)
        remainder = notional - (slices * max_slice_notional)
        result = [max_slice_notional] * slices
        if remainder > 0:
            result.append(remainder)
        return result

    def avoid_market_open(self, now: datetime) -> bool:
        open_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
        return 0 <= (now - open_time).total_seconds() / 60 < self.config.avoid_open_minutes

    def avoid_market_close(self, now: datetime) -> bool:
        close_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        return 0 <= (close_time - now).total_seconds() / 60 < self.config.avoid_close_minutes

    def avoid_news(self) -> bool:
        # No external news/webhook/API calls are allowed in LOCAL_ONLY mode. This conservative hook
        # is intentionally a no-op unless a future local-only calendar is provided.
        return False

    def in_trading_window(self, now: datetime) -> bool:
        if self.avoid_market_open(now) or self.avoid_market_close(now) or self.avoid_news():
            return False
        current = now.time()
        return any(_contains(window, current) for window in self.config.trading_windows)


def _contains(window: str, current: time) -> bool:
    start_raw, end_raw = window.split("-", 1)
    start = time.fromisoformat(start_raw)
    end = time.fromisoformat(end_raw)
    return start <= current <= end
