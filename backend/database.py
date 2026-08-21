"""Portable database access: SQLite by default, PostgreSQL via DATABASE_URL."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import get_settings
from .migrations import apply_migrations

logger = logging.getLogger(__name__)
DATABASE_PATH = Path(__file__).resolve().parent / "data" / "sumdle.db"


class DatabaseConnection:
    def __init__(self, connection: Any, dialect: str) -> None:
        self._connection = connection
        self.dialect = dialect

    def execute(self, query: str, parameters: tuple | list = ()):
        return self._connection.execute(self._query(query), parameters)

    def executemany(self, query: str, parameter_sets: list[tuple]):
        query = self._query(query)
        if self.dialect == "sqlite":
            return self._connection.executemany(query, parameter_sets)
        # psycopg exposes bulk execution on cursors, not Connection.
        with self._connection.cursor() as cursor:
            cursor.executemany(query, parameter_sets)

    def _query(self, query: str) -> str:
        """Translate the project's DB-API qmark placeholders for psycopg."""
        return query.replace("?", "%s") if self.dialect == "postgresql" else query

    def __enter__(self) -> "DatabaseConnection":
        self._connection.__enter__()
        return self

    def __exit__(self, *args: object) -> None:
        self._connection.__exit__(*args)


def _target(database_path: Path | str | None = None) -> tuple[str, Path | None]:
    if database_path is not None:
        return "sqlite", Path(database_path)
    url = get_settings().database_url
    if url and url.startswith(("postgres://", "postgresql://")):
        return "postgresql", None
    if url and url.startswith("sqlite:///"):
        return "sqlite", Path(url.removeprefix("sqlite:///"))
    if url:
        raise ValueError("DATABASE_URL must use postgresql://, postgres://, or sqlite:///")
    return "sqlite", DATABASE_PATH


def _open_connection(database_path: Path | str | None = None) -> DatabaseConnection:
    dialect, path = _target(database_path)
    if dialect == "sqlite":
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path)
        connection.row_factory = sqlite3.Row
        return DatabaseConnection(connection, dialect)
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:
        raise RuntimeError("PostgreSQL DATABASE_URL requires psycopg to be installed") from error
    # Never log the URL: it may contain credentials.
    return DatabaseConnection(psycopg.connect(get_settings().database_url, row_factory=dict_row), dialect)


def initialize_database(database_path: Path | str | None = None) -> None:
    """Apply outstanding migrations without deleting or replacing data."""
    connection = _open_connection(database_path)
    with connection:
        apply_migrations(connection, connection.dialect)
    logger.debug("Database schema is ready (%s)", connection.dialect)


def connect(database_path: Path | str | None = None) -> DatabaseConnection:
    initialize_database(database_path)
    return _open_connection(database_path)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()
