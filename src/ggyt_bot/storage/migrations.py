from __future__ import annotations

from pathlib import Path

from ggyt_bot.storage.database import TradingDatabase

MIGRATION_VERSION = 1


def migrate(path: Path) -> None:
    """Apply idempotent local SQLite migrations."""
    db = TradingDatabase(path)
    db.record("daily_stats", {"event": "migration", "version": MIGRATION_VERSION})
    db.close()
