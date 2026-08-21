"""Word validation and curated-solution services backed by SQLite."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date as date_type
from typing import Any

from . import database
from .mcp_client import McpUnavailableError, get_word_definition as get_mcp_word_definition
from .seed import seed_solutions


class NoActiveSolutionsError(RuntimeError):
    """The curated puzzle list has no active entries."""


def normalize_guess(word: str) -> str:
    return word.strip().lower() if isinstance(word, str) else ""


def is_structurally_valid(word: str) -> bool:
    normalized = normalize_guess(word)
    return len(normalized) == 5 and normalized.isascii() and normalized.isalpha()


def _prepare() -> None:
    database.initialize_database()
    seed_solutions()


def _cached_validation(word: str) -> dict[str, Any] | None:
    with database.connect() as connection:
        row = connection.execute(
            "SELECT valid, definition FROM word_validation_cache WHERE word = ?", (word,)
        ).fetchone()
    if row is None:
        return None
    result: dict[str, Any] = {"word": word, "valid": bool(row["valid"]), "source": "cache"}
    if row["definition"]:
        try:
            result["definition"] = json.loads(row["definition"])
        except json.JSONDecodeError:
            pass
    return result


def _store_validation(word: str, valid: bool, definition: dict[str, Any] | None) -> None:
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO word_validation_cache (word, valid, definition, checked_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(word) DO UPDATE SET valid = excluded.valid,
               definition = excluded.definition, checked_at = excluded.checked_at""",
            (word, int(valid), json.dumps(definition) if definition else None, database.now_iso()),
        )


async def validate_with_fallback(word: str) -> dict[str, str | bool | None]:
    """Validate with SQLite first, querying MCP only for uncached valid shapes."""
    normalized = normalize_guess(word)
    if not is_structurally_valid(normalized):
        return {"word": normalized, "valid": False, "source": "invalid"}
    _prepare()
    cached = _cached_validation(normalized)
    if cached is not None:
        return {key: value for key, value in cached.items() if key != "definition"}
    try:
        definition = await get_mcp_word_definition(normalized)
    except McpUnavailableError:
        return {"word": normalized, "valid": None, "source": "unavailable", "reason": "dictionary_lookup_unavailable"}
    valid = definition is not None
    _store_validation(normalized, valid, definition)
    return {"word": normalized, "valid": valid, "source": "mcp"}


async def get_word_definition(word: str) -> dict[str, Any] | None:
    normalized = normalize_guess(word)
    if not is_structurally_valid(normalized):
        return None
    _prepare()
    cached = _cached_validation(normalized)
    if cached is not None:
        return cached.get("definition")
    definition = await get_mcp_word_definition(normalized)
    _store_validation(normalized, definition is not None, definition)
    return definition


def get_all_active_solutions() -> tuple[str, ...]:
    _prepare()
    with database.connect() as connection:
        rows = connection.execute("SELECT word FROM solutions WHERE active = 1 ORDER BY word").fetchall()
    return tuple(row["word"] for row in rows)


def solution_exists(word: str) -> bool:
    _prepare()
    with database.connect() as connection:
        return connection.execute("SELECT 1 FROM solutions WHERE word = ? AND active = 1", (normalize_guess(word),)).fetchone() is not None


def get_random_solution(exclude: set[str] | None = None) -> str:
    solutions = get_all_active_solutions()
    if not solutions:
        raise NoActiveSolutionsError("No active solutions are available")
    excluded = {normalize_guess(word) for word in (exclude or set())}
    return random.choice(tuple(word for word in solutions if word not in excluded) or solutions)


def get_daily_solution(date: date_type | None = None) -> str:
    puzzle_date = date or date_type.today()
    if not isinstance(puzzle_date, date_type):
        raise TypeError("date must be a datetime.date or None")
    solutions = get_all_active_solutions()
    if not solutions:
        raise NoActiveSolutionsError("No active solutions are available")
    digest = hashlib.sha256(puzzle_date.isoformat().encode("utf-8")).digest()
    return solutions[int.from_bytes(digest, byteorder="big") % len(solutions)]
