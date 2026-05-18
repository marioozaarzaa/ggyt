from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class OHLCVSeries:
    symbol: str
    timestamps: list[datetime]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    volume: list[float]

    @property
    def age_seconds(self) -> float:
        if not self.timestamps:
            return float("inf")
        latest = self.timestamps[-1]
        if latest.tzinfo is None:
            latest = latest.replace(tzinfo=UTC)
        return max(0.0, (datetime.now(UTC) - latest).total_seconds())

    @classmethod
    def from_closes(cls, symbol: str, closes: list[float]) -> OHLCVSeries:
        now = datetime.now(UTC)
        timestamps = [now for _ in closes]
        return cls(
            symbol, timestamps, closes[:], closes[:], closes[:], closes[:], [1.0] * len(closes)
        )
