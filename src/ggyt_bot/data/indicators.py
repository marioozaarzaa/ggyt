from __future__ import annotations

import math
from collections.abc import Sequence


def sma(values: Sequence[float], window: int) -> float | None:
    if window <= 0 or len(values) < window:
        return None
    return sum(values[-window:]) / window


def ema_series(values: Sequence[float], window: int) -> list[float]:
    if window <= 0 or not values:
        return []
    alpha = 2 / (window + 1)
    result = [float(values[0])]
    for value in values[1:]:
        result.append((float(value) * alpha) + (result[-1] * (1 - alpha)))
    return result


def ema(values: Sequence[float], window: int) -> float | None:
    series = ema_series(values, window)
    return series[-1] if len(values) >= window and series else None


def rsi(values: Sequence[float], window: int = 14) -> float | None:
    if len(values) <= window:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(values[-window - 1 : -1], values[-window:], strict=False):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values: Sequence[float]) -> tuple[float | None, float | None, float | None]:
    if len(values) < 35:
        return None, None, None
    fast = ema_series(values, 12)
    slow = ema_series(values, 26)
    aligned = [f - s for f, s in zip(fast[-len(slow) :], slow, strict=False)]
    signal_series = ema_series(aligned, 9)
    macd_line = aligned[-1]
    signal_line = signal_series[-1]
    return macd_line, signal_line, macd_line - signal_line


def atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    window: int = 14,
) -> float | None:
    if len(highs) < window + 1 or len(lows) < window + 1 or len(closes) < window + 1:
        return None
    true_ranges: list[float] = []
    start = len(closes) - window
    for index in range(start, len(closes)):
        high = highs[index]
        low = lows[index]
        previous_close = closes[index - 1]
        true_ranges.append(max(high - low, abs(high - previous_close), abs(low - previous_close)))
    return sum(true_ranges) / window


def relative_volume(volumes: Sequence[float], window: int = 20) -> float | None:
    if len(volumes) < window + 1:
        return None
    baseline = sum(volumes[-window - 1 : -1]) / window
    if baseline == 0:
        return None
    return volumes[-1] / baseline


def volatility(values: Sequence[float], window: int = 20) -> float | None:
    if len(values) <= window:
        return None
    returns = [
        (current - previous) / previous
        for previous, current in zip(values[-window - 1 : -1], values[-window:], strict=False)
        if previous
    ]
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((item - mean) ** 2 for item in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(252)


def spread_pct(
    bid: float | None,
    ask: float | None,
    fallback_price: float | None = None,
) -> float | None:
    if bid is not None and ask is not None and bid > 0 and ask >= bid:
        midpoint = (bid + ask) / 2
        return (ask - bid) / midpoint if midpoint else None
    if fallback_price and fallback_price > 0:
        return 0.0005
    return None
