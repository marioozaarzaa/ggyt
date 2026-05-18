from __future__ import annotations

from ggyt_bot.models import AccountSnapshot, PositionSnapshot, StrategyDecision
from ggyt_bot.settings import BotConfig
from ggyt_bot.state import BotState


class RiskManager:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def halt_reason(
        self,
        account: AccountSnapshot,
        positions: list[PositionSnapshot],
        state: BotState,
    ) -> str | None:
        state.rollover_if_needed(account.equity)
        if state.kill_switch_enabled:
            return state.halt_reason or "global kill switch enabled"
        if state.halted:
            return state.halt_reason or "bot already halted"

        if account.equity < self.config.risk.minimum_equity:
            return f"account equity below minimum ({account.equity:.2f})"

        if (
            self.config.risk.stop_on_any_loss
            and state.day_start_equity is not None
            and account.equity < state.day_start_equity
        ):
            return (
                f"equity below day start ({account.equity:.2f} < "
                f"{state.day_start_equity:.2f}); stop_on_any_loss enabled"
            )

        if state.day_start_equity:
            daily_loss_pct = (state.day_start_equity - account.equity) / state.day_start_equity
            if daily_loss_pct >= self.config.risk.max_daily_loss_pct:
                return f"daily loss limit reached ({daily_loss_pct:.4%})"

        if state.high_watermark_equity:
            drawdown_pct = (
                state.high_watermark_equity - account.equity
            ) / state.high_watermark_equity
            if drawdown_pct >= self.config.risk.max_drawdown_pct:
                return f"max drawdown reached ({drawdown_pct:.4%})"

        total_exposure = sum(max(0.0, position.market_value) for position in positions)
        if (
            account.equity > 0
            and total_exposure / account.equity > self.config.risk.max_total_exposure_pct
        ):
            return "max total exposure exceeded"

        for position in positions:
            if position.market_value > 0 and position.unrealized_pl < 0:
                loss_pct = abs(position.unrealized_pl) / position.market_value
                if loss_pct >= self.config.risk.per_position_stop_loss_pct:
                    return f"{position.symbol} position stop loss reached ({loss_pct:.4%})"
        return None

    def allowed_notional(
        self,
        account: AccountSnapshot,
        positions: list[PositionSnapshot],
        decision: StrategyDecision,
        atr: float | None = None,
        price: float | None = None,
    ) -> float:
        del decision
        from ggyt_bot.risk.position_sizing import atr_risk_position_size

        current_exposure = sum(max(0.0, position.market_value) for position in positions)
        max_total = account.equity * self.config.risk.max_total_exposure_pct
        remaining_exposure = max(0.0, max_total - current_exposure)
        max_position = account.equity * self.config.risk.max_position_notional_pct
        reserve_cash = account.equity * self.config.execution.min_cash_reserve_pct
        spendable_cash = max(0.0, account.cash - reserve_cash)
        cap = max(0.0, min(max_position, remaining_exposure, spendable_cash, account.buying_power))
        if atr is not None and price is not None:
            sized = atr_risk_position_size(
                equity=account.equity,
                price=price,
                atr=atr,
                risk_fraction=self.config.risk.max_risk_per_trade_pct,
                atr_multiplier=2.0,
                max_notional=cap,
            )
            return sized.notional
        return cap


__all__ = ["RiskManager"]
