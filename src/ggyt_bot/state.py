from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path


@dataclass
class BotState:
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    trading_day: date = field(default_factory=lambda: datetime.now(UTC).date())
    day_start_equity: float | None = None
    high_watermark_equity: float | None = None
    halted: bool = False
    halt_reason: str | None = None
    kill_switch_enabled: bool = False
    open_orders_synced: bool = False
    positions_synced: bool = False

    @classmethod
    def load(cls, path: Path) -> BotState:
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["created_at"] = datetime.fromisoformat(raw["created_at"])
        raw["trading_day"] = date.fromisoformat(raw["trading_day"])
        return cls(**raw)

    def rollover_if_needed(self, current_equity: float) -> None:
        today = datetime.now(UTC).date()
        if self.trading_day != today:
            self.trading_day = today
            self.day_start_equity = current_equity
            self.halted = False
            self.halt_reason = None
            self.kill_switch_enabled = False
        if self.day_start_equity is None:
            self.day_start_equity = current_equity
        if self.high_watermark_equity is None or current_equity > self.high_watermark_equity:
            self.high_watermark_equity = current_equity

    def halt(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason

    def kill_switch(self, reason: str) -> None:
        self.kill_switch_enabled = True
        self.halt(reason)

    def save(self, path: Path) -> None:
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat()
        payload["trading_day"] = self.trading_day.isoformat()
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
