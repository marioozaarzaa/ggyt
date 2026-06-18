from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ggyt_bot.storage.database import TradingDatabase


class MemoryManager:
    """Handles Jarvis's long-term and short-term memory using the local database."""

    def __init__(self, database: TradingDatabase) -> None:
        self.database = database

    def store_insight(self, category: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "type": category,
            "thought": content,
            "metadata": metadata or {},
        }
        self.database.record("jarvis_memory", payload)

    def get_recent_insights(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.database.latest("jarvis_memory", limit)

    def set_preference(self, key: str, value: Any) -> None:
        payload = {
            "ts": datetime.now(UTC).isoformat(),
            "key": key,
            "value": value,
        }
        self.database.record("user_preferences", payload)

    def get_preferences(self) -> dict[str, Any]:
        records = self.database.latest("user_preferences", 100)
        # Return a flattened dict of latest values per key
        prefs = {}
        for rec in reversed(records):
            prefs[rec["key"]] = rec["value"]
        return prefs
