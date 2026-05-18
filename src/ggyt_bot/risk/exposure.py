from __future__ import annotations

from ggyt_bot.models import PositionSnapshot


def total_exposure(positions: list[PositionSnapshot]) -> float:
    return sum(max(0.0, position.market_value) for position in positions)


def exposure_pct(positions: list[PositionSnapshot], equity: float) -> float:
    return total_exposure(positions) / equity if equity > 0 else 0.0


def exposure_available(
    positions: list[PositionSnapshot], equity: float, max_exposure_pct: float
) -> float:
    return max(0.0, (equity * max_exposure_pct) - total_exposure(positions))
