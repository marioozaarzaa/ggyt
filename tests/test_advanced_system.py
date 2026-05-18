from datetime import datetime

from ggyt_bot.adaptive.parameter_tuner import AdaptiveParameters, LimitedAdaptiveTuner
from ggyt_bot.analytics.trade_analyzer import TradeAnalyzer
from ggyt_bot.data.feature_engine import build_features
from ggyt_bot.data.market_data import OHLCVSeries
from ggyt_bot.data.market_regime import MarketRegime, detect_market_regime
from ggyt_bot.execution.execution_engine import ExecutionEngine
from ggyt_bot.risk.circuit_breaker import CircuitBreaker
from ggyt_bot.settings import ExecutionConfig
from ggyt_bot.strategies.ensemble import EnsembleStrategy
from ggyt_bot.strategies.strategy_base import StrategyContext


def test_ensemble_strategy_returns_scored_signal() -> None:
    closes = [100 + i * 0.05 for i in range(240)]
    series = OHLCVSeries.from_closes("SPY", closes)
    features = build_features(series)
    decision = EnsembleStrategy().generate_signal(StrategyContext("SPY", series, features))

    assert decision.score != 0
    assert 0 <= decision.confidence <= 1


def test_market_regime_detects_panic_for_high_volatility() -> None:
    closes = [100 + ((-1) ** i) * i for i in range(240)]
    series = OHLCVSeries.from_closes("SPY", closes)

    assert detect_market_regime(build_features(series)) is MarketRegime.PANIC


def test_execution_engine_blocks_wide_spread() -> None:
    closes = [100 + i * 0.01 for i in range(240)]
    features = build_features(OHLCVSeries.from_closes("SPY", closes))
    features = features.__class__(**{**features.__dict__, "spread_pct": 0.10})
    engine = ExecutionEngine(ExecutionConfig(trading_windows=["00:00-23:59"]))

    decision = engine.validate_trade(
        notional=10_000, features=features, now=datetime(2026, 1, 1, 10)
    )

    assert not decision.allowed
    assert "spread" in decision.reason


def test_circuit_breaker_stops_after_three_losses() -> None:
    breaker = CircuitBreaker(max_consecutive_losses=3)
    breaker.record_trade_result(-1)
    breaker.record_trade_result(-1)
    breaker.record_trade_result(-1)

    assert breaker.state.stopped_until is not None


def test_limited_adaptive_tuner_stays_within_bounds() -> None:
    tuner = LimitedAdaptiveTuner()
    proposed = tuner.propose(win_rate=0.40, max_drawdown=0.06)

    proposed.validate()
    assert 0.5 <= proposed.risk_multiplier <= 2


def test_adaptive_parameters_validate_bounds() -> None:
    AdaptiveParameters(ema_fast=10, stop_multiplier=1, risk_multiplier=0.5).validate()


def test_trade_analyzer_groups_win_rates() -> None:
    analysis = TradeAnalyzer().analyze(
        [
            {"ts": "2026-01-01T10:00:00+00:00", "pnl": 10, "strategy": "trend"},
            {"ts": "2026-01-01T10:30:00+00:00", "pnl": -5, "strategy": "trend"},
        ]
    )

    assert analysis.win_rate_by_hour[10] == 0.5
    assert analysis.win_rate_by_strategy["trend"] == 0.5
