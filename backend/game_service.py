"""Server-authoritative Sumdle game sessions."""

from __future__ import annotations

import json
import time as system_time
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from . import database
from .player_stats import record_result, register_player
from .mcp_client import McpUnavailableError
from .word_service import get_daily_solution, get_random_solution, get_word_definition, normalize_guess, validate_with_fallback


def _uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as error:
        raise ValueError("invalid game id") from error


def evaluate_guess(guess: str, solution: str) -> list[str]:
    result = ["absent"] * 5
    remaining = list(solution)
    for index, letter in enumerate(guess):
        if letter == solution[index]:
            result[index] = "correct"
            remaining[index] = ""
    for index, letter in enumerate(guess):
        if result[index] != "correct" and letter in remaining:
            result[index] = "present"
            remaining[remaining.index(letter)] = ""
    return result


def _next_daily_reset_at() -> str:
    """Return the next server-local calendar boundary as an aware timestamp."""
    next_day = date.today() + timedelta(days=1)
    local_midnight = system_time.mktime((next_day.year, next_day.month, next_day.day, 0, 0, 0, 0, 0, -1))
    return datetime.fromtimestamp(local_midnight).astimezone().isoformat()


def _session(connection, row):
    guesses = connection.execute("SELECT guess, result FROM game_guesses WHERE game_id = ? ORDER BY attempt_number", (row["id"],)).fetchall()
    data = {"game_id": row["id"], "mode": row["mode"], "status": row["status"], "attempts": row["attempts"], "hint_count": row["hint_count"], "guesses": [{"word": guess["guess"], "result": json.loads(guess["result"])} for guess in guesses]}
    if row["status"] != "playing":
        data["solution"] = row["solution"]
    if row["mode"] == "daily":
        data["next_daily_reset_at"] = _next_daily_reset_at()
    return data


def start_game(player_id: str, mode: str) -> dict:
    player_id = register_player(player_id)
    if mode not in {"daily", "unlimited"}:
        raise ValueError("invalid mode")
    today = date.today().isoformat() if mode == "daily" else None
    with database.connect() as connection:
        if mode == "daily":
            row = connection.execute("SELECT * FROM game_sessions WHERE player_id = ? AND mode = 'daily' AND puzzle_date = ?", (player_id, today)).fetchone()
            if row:
                return _session(connection, row)
        solution = get_daily_solution(date.fromisoformat(today)) if mode == "daily" else get_random_solution()
        game_id = str(uuid4())
        connection.execute("INSERT INTO game_sessions (id, player_id, mode, puzzle_date, solution, status, attempts, hint_count, created_at) VALUES (?, ?, ?, ?, ?, 'playing', 0, 0, ?)", (game_id, player_id, mode, today, solution, database.now_iso()))
        row = connection.execute("SELECT * FROM game_sessions WHERE id = ?", (game_id,)).fetchone()
        return _session(connection, row)


def get_game(game_id: str) -> dict:
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM game_sessions WHERE id = ?", (_uuid(game_id),)).fetchone()
        if not row:
            raise LookupError("game not found")
        return _session(connection, row)


async def submit_guess(game_id: str, guess: str) -> dict:
    game_id = _uuid(game_id)
    guess = normalize_guess(guess)
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM game_sessions WHERE id = ?", (game_id,)).fetchone()
        if not row:
            raise LookupError("game not found")
        if row["status"] != "playing":
            raise ValueError("game is already complete")
        validation = await validate_with_fallback(guess)
        if validation["valid"] is not True:
            return {**_session(connection, row), "accepted": False, "message": "dictionary is taking a little break" if validation["source"] == "unavailable" else "not in the word list"}
        attempts = row["attempts"] + 1
        states = evaluate_guess(guess, row["solution"])
        status = "won" if guess == row["solution"] else "lost" if attempts == 6 else "playing"
        completed = database.now_iso() if status != "playing" else None
        connection.execute("INSERT INTO game_guesses (game_id, guess, result, attempt_number, created_at) VALUES (?, ?, ?, ?, ?)", (game_id, guess, json.dumps(states), attempts, database.now_iso()))
        connection.execute("UPDATE game_sessions SET attempts = ?, status = ?, completed_at = ? WHERE id = ?", (attempts, status, completed, game_id))
        row = connection.execute("SELECT * FROM game_sessions WHERE id = ?", (game_id,)).fetchone()
    data = get_game(game_id)
    data["accepted"] = True
    if status != "playing":
        data["stats"] = record_result(row["player_id"], row["mode"], attempts, status == "won", row["puzzle_date"], row["solution"])["stats"]
    return data


def _sanitize(text: str, solution: str) -> str:
    return " ".join(text.replace(solution, "this word").replace(solution.capitalize(), "this word").split())


async def get_hint(game_id: str, level: int) -> dict:
    if level not in {1, 2}:
        raise ValueError("hint level must be 1 or 2")
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM game_sessions WHERE id = ?", (_uuid(game_id),)).fetchone()
        if not row:
            raise LookupError("game not found")
        if row["status"] != "playing":
            raise ValueError("game is already complete")
        if row["hint_count"] >= 2:
            raise ValueError("all tiny hints have been used")
        connection.execute("UPDATE game_sessions SET hint_count = hint_count + 1 WHERE id = ?", (row["id"],))
        hint_count = row["hint_count"] + 1
    try:
        definition = await get_word_definition(row["solution"])
    except McpUnavailableError:
        return {"hint_count": hint_count, "hint": "a little clue is resting right now — try another guess ✦", "available": False}
    if not definition or not definition.get("definitions"):
        return {"hint_count": hint_count, "hint": "this is a familiar English word with five letters ✦", "available": True}
    entry = definition["definitions"][0]
    if level == 1:
        part = entry.get("part_of_speech") or "word"
        hint = f"this word is commonly used as a {part}"
    else:
        hint = _sanitize(str(entry.get("definition", "")), row["solution"])
    return {"hint_count": hint_count, "hint": hint or "this word has a gentle everyday meaning ✦", "available": True}


async def get_definition(game_id: str) -> dict:
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM game_sessions WHERE id = ?", (_uuid(game_id),)).fetchone()
    if not row:
        raise LookupError("game not found")
    if row["status"] == "playing":
        raise PermissionError("definition is available after the game")
    try:
        definition = await get_word_definition(row["solution"])
    except McpUnavailableError:
        return {"word": row["solution"], "available": False}
    if not definition:
        return {"word": row["solution"], "available": False}
    entry = definition.get("definitions", [{}])[0]
    return {"word": row["solution"], "available": True, "part_of_speech": entry.get("part_of_speech"), "definition": entry.get("definition"), "phonetic": definition.get("phonetic")}
