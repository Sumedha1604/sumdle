"""Fast, cached access to Sumdle's word banks."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import date as date_type
from pathlib import Path

from .mcp_client import get_word_definition as get_mcp_word_definition

DATA_DIR = Path(__file__).resolve().parent / "data"


def _load_bank(filename: str) -> tuple[str, ...]:
    with (DATA_DIR / filename).open(encoding="utf-8") as source:
        return tuple(json.load(source))


SOLUTIONS = _load_bank("solutions.json")
VALID_GUESSES = _load_bank("valid_guesses.json")
SOLUTION_SET = frozenset(SOLUTIONS)
VALID_GUESS_SET = frozenset(VALID_GUESSES)


def normalize_guess(word: str) -> str:
    """Normalize user input without accepting non-string values."""
    return word.strip().lower() if isinstance(word, str) else ""


def is_valid_guess(word: str) -> bool:
    """Return whether the normalized input is in the accepted-guess set."""
    return normalize_guess(word) in VALID_GUESS_SET


async def validate_with_fallback(word: str) -> dict[str, str | bool]:
    """Validate locally first, using the optional MCP dictionary only on misses."""
    normalized = normalize_guess(word)
    if normalized in VALID_GUESS_SET:
        return {"word": normalized, "valid": True, "source": "local"}
    if len(normalized) != 5 or not normalized.isalpha():
        return {"word": normalized, "valid": False, "source": "invalid"}
    definition = await get_mcp_word_definition(normalized)
    return {"word": normalized, "valid": definition is not None, "source": "mcp" if definition else "unavailable"}


async def get_word_definition(word: str) -> dict | None:
    """Get normalized dictionary data without coupling callers to MCP objects."""
    return await get_mcp_word_definition(normalize_guess(word))


def get_random_solution(exclude: set[str] | None = None) -> str:
    """Choose a solution, preferring one not present in ``exclude``.

    If all solutions are excluded, the full bank is used so this function always
    returns a playable puzzle.
    """
    excluded = {normalize_guess(word) for word in (exclude or set())}
    choices = tuple(word for word in SOLUTIONS if word not in excluded) or SOLUTIONS
    return random.choice(choices)


def get_daily_solution(date: date_type | None = None) -> str:
    """Map a calendar date to a stable answer using SHA-256."""
    puzzle_date = date or date_type.today()
    if not isinstance(puzzle_date, date_type):
        raise TypeError("date must be a datetime.date or None")
    digest = hashlib.sha256(puzzle_date.isoformat().encode("utf-8")).digest()
    index = int.from_bytes(digest, byteorder="big") % len(SOLUTIONS)
    return SOLUTIONS[index]
