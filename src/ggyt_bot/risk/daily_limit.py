from __future__ import annotations


def daily_loss_pct(equity: float, day_start_equity: float | None) -> float:
    if not day_start_equity or day_start_equity <= 0:
        return 0.0
    return max(0.0, (day_start_equity - equity) / day_start_equity)


def exceeds_daily_loss(equity: float, day_start_equity: float | None, limit: float) -> bool:
    return daily_loss_pct(equity, day_start_equity) >= limit
