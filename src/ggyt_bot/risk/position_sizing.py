from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizingResult:
    shares: float
    notional: float
    risk_amount: float
    stop_distance: float


def atr_risk_position_size(
    *,
    equity: float,
    price: float,
    atr: float | None,
    risk_fraction: float = 0.005,
    atr_multiplier: float = 2.0,
    max_notional: float | None = None,
) -> PositionSizingResult:
    if equity <= 0 or price <= 0 or atr is None or atr <= 0:
        return PositionSizingResult(0.0, 0.0, 0.0, 0.0)
    risk_amount = equity * risk_fraction
    stop_distance = atr * atr_multiplier
    shares = risk_amount / stop_distance
    notional = shares * price
    if max_notional is not None and notional > max_notional:
        notional = max_notional
        shares = notional / price
    return PositionSizingResult(shares, notional, risk_amount, stop_distance)
