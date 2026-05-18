from __future__ import annotations

from enum import StrEnum

from ggyt_bot.data.feature_engine import FeatureSet


class MarketRegime(StrEnum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    PANIC = "PANIC"


def detect_market_regime(features: FeatureSet) -> MarketRegime:
    volatility = features.volatility20 or 0.0
    atr = features.atr14 or 0.0
    price = features.last_close or 0.0
    atr_pct = atr / price if price else 0.0
    if volatility >= 0.45 or atr_pct >= 0.08:
        return MarketRegime.PANIC
    if volatility >= 0.30 or atr_pct >= 0.04:
        return MarketRegime.HIGH_VOLATILITY
    if volatility <= 0.08 and atr_pct <= 0.015:
        return MarketRegime.LOW_VOLATILITY
    if (
        features.ema20 is not None
        and features.ema50 is not None
        and features.ema200 is not None
        and ((features.ema20 > features.ema50 > features.ema200)
             or (features.ema20 < features.ema50 < features.ema200))
    ):
        return MarketRegime.TRENDING
    return MarketRegime.RANGING


def regime_position_multiplier(regime: MarketRegime) -> float:
    return {
        MarketRegime.TRENDING: 1.0,
        MarketRegime.RANGING: 0.75,
        MarketRegime.HIGH_VOLATILITY: 0.5,
        MarketRegime.LOW_VOLATILITY: 0.75,
        MarketRegime.PANIC: 0.0,
    }[regime]
