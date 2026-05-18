from ggyt_bot.models import AccountSnapshot, PositionSnapshot
from ggyt_bot.risk import RiskManager
from ggyt_bot.settings import BotConfig, RiskConfig
from ggyt_bot.state import BotState


def test_stop_on_any_loss_halts_when_equity_drops() -> None:
    risk = RiskManager(BotConfig(risk=RiskConfig(stop_on_any_loss=True)))
    state = BotState(day_start_equity=100_000, high_watermark_equity=100_000)

    reason = risk.halt_reason(AccountSnapshot(99_999, 50_000, 50_000), [], state)

    assert reason is not None
    assert "stop_on_any_loss" in reason


def test_per_position_stop_loss_halts() -> None:
    risk = RiskManager(
        BotConfig(risk=RiskConfig(stop_on_any_loss=False, per_position_stop_loss_pct=0.01))
    )
    state = BotState(day_start_equity=100_000, high_watermark_equity=100_000)
    positions = [PositionSnapshot("SPY", 10_000, -150, 10, 1_015, 1_000)]

    reason = risk.halt_reason(AccountSnapshot(100_000, 90_000, 90_000), positions, state)

    assert reason is not None
    assert "stop loss" in reason
