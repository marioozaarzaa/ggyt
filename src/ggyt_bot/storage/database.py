from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TABLES = (
    "trades",
    "orders",
    "signals",
    "positions",
    "daily_stats",
    "errors",
    "market_conditions",
    "adaptive_adjustments",
    "backtests",
    "jarvis_memory",
    "user_preferences",
)


@dataclass(frozen=True)
class StorageRecord:
    table: str
    payload: dict[str, Any]
    created_at: datetime | None = None


class TradingDatabase:
    """SQLite storage with a SQLAlchemy ORM path when SQLAlchemy is installed.

    The project declares SQLAlchemy as a dependency. The sqlite3 fallback keeps local tests and
    emergency recovery usable in restricted environments where dependencies cannot be downloaded.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self.initialize()

    def initialize(self) -> None:
        for table in TABLES:
            self._conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
        self._conn.commit()

    def record(self, table: str, payload: dict[str, Any]) -> int:
        if table not in TABLES:
            raise ValueError(f"unknown table {table}")
        created_at = datetime.now(UTC).isoformat()
        cursor = self._conn.execute(
            f"INSERT INTO {table} (created_at, payload) VALUES (?, ?)",
            (created_at, json.dumps(payload, sort_keys=True, default=str)),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def latest(self, table: str, limit: int = 20) -> list[dict[str, Any]]:
        if table not in TABLES:
            raise ValueError(f"unknown table {table}")
        rows = self._conn.execute(
            f"SELECT id, created_at, payload FROM {table} ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"id": row["id"], "created_at": row["created_at"], **json.loads(row["payload"])}
            for row in rows
        ]

    def close(self) -> None:
        self._conn.close()


try:
    from sqlalchemy import (  # type: ignore[import-not-found]
        JSON,
        DateTime,
        Integer,
        String,
        create_engine,
    )
    from sqlalchemy.orm import (  # type: ignore[import-not-found]
        DeclarativeBase,
        Mapped,
        mapped_column,
        sessionmaker,
    )

    class Base(DeclarativeBase):
        pass

    class EventRecord(Base):
        __tablename__ = "event_records"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        table_name: Mapped[str] = mapped_column(String(64), index=True)
        created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
        payload: Mapped[dict[str, Any]] = mapped_column(JSON)

    class SQLAlchemyTradingDatabase(TradingDatabase):
        def __init__(self, path: Path) -> None:
            self.path = path
            if path.parent != Path("."):
                self.path.parent.mkdir(parents=True, exist_ok=True)
            self.engine = create_engine(f"sqlite:///{path}")
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            super().__init__(path)

        def record(self, table: str, payload: dict[str, Any]) -> int:
            row_id = super().record(table, payload)
            with self.Session() as session:
                session.add(
                    EventRecord(table_name=table, created_at=datetime.now(UTC), payload=payload)
                )
                session.commit()
            return row_id

except ModuleNotFoundError:
    SQLAlchemyTradingDatabase = TradingDatabase  # type: ignore[misc,assignment]
    EventRecord = None  # type: ignore[assignment]


def record_from_dataclass(table: str, value: object) -> StorageRecord:
    payload = asdict(value) if hasattr(value, "__dataclass_fields__") else {"value": str(value)}
    return StorageRecord(table=table, payload=payload, created_at=datetime.now(UTC))
