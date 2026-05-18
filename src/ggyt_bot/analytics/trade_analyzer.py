from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TradeAnalysis:
    best_hours: list[int]
    worst_hours: list[int]
    win_rate_by_hour: dict[int, float]
    win_rate_by_strategy: dict[str, float]
    best_conditions: list[str]
    worst_conditions: list[str]


class TradeAnalyzer:
    def analyze(self, trades: list[dict[str, Any]]) -> TradeAnalysis:
        by_hour: dict[int, list[bool]] = defaultdict(list)
        by_strategy: dict[str, list[bool]] = defaultdict(list)
        by_condition: dict[str, list[bool]] = defaultdict(list)
        for trade in trades:
            pnl = float(trade.get("pnl", trade.get("profit", 0.0)))
            won = pnl > 0
            ts = str(trade.get("time", trade.get("ts", "")))
            hour = _safe_hour(ts)
            if hour is not None:
                by_hour[hour].append(won)
            by_strategy[str(trade.get("strategy", "unknown"))].append(won)
            condition = str(trade.get("market_regime", trade.get("market", "unknown")))
            by_condition[condition].append(won)
        hour_rates = {hour: _win_rate(values) for hour, values in by_hour.items()}
        strategy_rates = {name: _win_rate(values) for name, values in by_strategy.items()}
        condition_rates = {name: _win_rate(values) for name, values in by_condition.items()}
        best_hours = sorted(hour_rates, key=hour_rates.get, reverse=True)[:3]
        worst_hours = sorted(hour_rates, key=hour_rates.get)[:3]
        best_conditions = sorted(condition_rates, key=condition_rates.get, reverse=True)[:3]
        worst_conditions = sorted(condition_rates, key=condition_rates.get)[:3]
        return TradeAnalysis(
            best_hours,
            worst_hours,
            hour_rates,
            strategy_rates,
            best_conditions,
            worst_conditions,
        )


def _safe_hour(raw: str) -> int | None:
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).hour
    except ValueError:
        return None


def _win_rate(values: list[bool]) -> float:
    return sum(1 for value in values if value) / len(values) if values else 0.0
