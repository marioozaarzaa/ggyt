from __future__ import annotations

from dataclasses import dataclass

from ggyt_bot.models import AccountSnapshot, PositionSnapshot
from ggyt_bot.risk.exposure import exposure_available, exposure_pct, total_exposure


@dataclass(frozen=True)
class PortfolioSnapshot:
    equity: float
    cash: float
    buying_power: float
    pnl_open: float
    pnl_daily: float
    pnl_total: float
    exposure: float
    exposure_pct: float
    risk_used: float
    risk_available: float
    free_capital: float
    positions: list[PositionSnapshot]


class PortfolioManager:
    def __init__(
        self,
        max_exposure_pct: float,
        max_risk_pct: float = 0.005,
        starting_equity: float | None = None,
        day_start_equity: float | None = None,
    ) -> None:
        self.max_exposure_pct = max_exposure_pct
        self.max_risk_pct = max_risk_pct
        self.starting_equity = starting_equity
        self.day_start_equity = day_start_equity

    def snapshot(
        self, account: AccountSnapshot, positions: list[PositionSnapshot]
    ) -> PortfolioSnapshot:
        exposure = total_exposure(positions)
        open_risk = sum(max(0.0, -position.unrealized_pl) for position in positions)
        max_risk = account.equity * self.max_risk_pct * max(1, len(positions) or 1)
        return PortfolioSnapshot(
            equity=account.equity,
            cash=account.cash,
            buying_power=account.buying_power,
            pnl_open=sum(position.unrealized_pl for position in positions),
            pnl_daily=account.equity - (self.day_start_equity or account.equity),
            pnl_total=account.equity - (self.starting_equity or account.equity),
            exposure=exposure,
            exposure_pct=exposure_pct(positions, account.equity),
            risk_used=open_risk,
            risk_available=max(0.0, max_risk - open_risk),
            free_capital=max(0.0, account.cash - exposure),
            positions=positions,
        )

    def available_exposure(
        self, account: AccountSnapshot, positions: list[PositionSnapshot]
    ) -> float:
        return exposure_available(positions, account.equity, self.max_exposure_pct)
