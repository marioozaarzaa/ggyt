from __future__ import annotations

from dataclasses import dataclass

from ggyt_bot.data.indicators import atr, ema, macd, relative_volume, rsi, spread_pct, volatility
from ggyt_bot.data.market_data import OHLCVSeries


@dataclass(frozen=True)
class FeatureSet:
    ema20: float | None
    ema50: float | None
    ema200: float | None
    rsi14: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    atr14: float | None
    relative_volume20: float | None
    volatility20: float | None
    spread_pct: float | None
    last_close: float | None


def build_features(series: OHLCVSeries) -> FeatureSet:
    macd_line, signal_line, histogram = macd(series.close)
    last_close = series.close[-1] if series.close else None
    return FeatureSet(
        ema20=ema(series.close, 20),
        ema50=ema(series.close, 50),
        ema200=ema(series.close, 200),
        rsi14=rsi(series.close, 14),
        macd=macd_line,
        macd_signal=signal_line,
        macd_histogram=histogram,
        atr14=atr(series.high, series.low, series.close, 14),
        relative_volume20=relative_volume(series.volume, 20),
        volatility20=volatility(series.close, 20),
        spread_pct=spread_pct(None, None, last_close),
        last_close=last_close,
    )
