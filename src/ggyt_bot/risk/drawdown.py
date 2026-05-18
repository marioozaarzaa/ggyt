from __future__ import annotations


def drawdown_pct(equity: float, high_watermark: float | None) -> float:
    if not high_watermark or high_watermark <= 0:
        return 0.0
    return max(0.0, (high_watermark - equity) / high_watermark)


def exceeds_drawdown(equity: float, high_watermark: float | None, max_drawdown: float) -> bool:
    return drawdown_pct(equity, high_watermark) >= max_drawdown
