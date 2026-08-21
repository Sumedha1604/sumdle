"""Small SQLite persistence layer for Sumdle's curated words and MCP cache."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "data" / "sumdle.db"


def _path(database_path: Path | str | None = None) -> Path:
    return Path(database_path) if database_path is not None else DATABASE_PATH


def initialize_database(database_path: Path | str | None = None) -> None:
    """Create required tables without modifying existing rows."""
    path = _path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("""CREATE TABLE IF NOT EXISTS solutions (
            id INTEGER PRIMARY KEY, word TEXT UNIQUE NOT NULL, difficulty TEXT,
            active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS word_validation_cache (
            word TEXT PRIMARY KEY, valid INTEGER NOT NULL, definition TEXT,
            checked_at TEXT NOT NULL)""")


def connect(database_path: Path | str | None = None) -> sqlite3.Connection:
    path = _path(database_path)
    initialize_database(path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
