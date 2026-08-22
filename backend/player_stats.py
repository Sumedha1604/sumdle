"""Anonymous player registration, completed-game recording, and statistics."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from . import database
from .word_service import get_daily_solution, normalize_guess


def _player_id(player_id: str) -> str:
    try:
        return str(UUID(player_id))
    except (TypeError, ValueError) as error:
        raise ValueError("player_id must be a UUID") from error


def register_player(player_id: str) -> str:
    player_id = _player_id(player_id)
    now = database.now_iso()
    with database.connect() as connection:
        connection.execute("INSERT INTO players (id, created_at, last_seen_at) VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET last_seen_at = excluded.last_seen_at", (player_id, now, now))
    return player_id


def _daily_streak(rows) -> tuple[int, int]:
    running = maximum = 0
    previous_date: date | None = None
    for row in rows:
        puzzle_date = date.fromisoformat(row["puzzle_date"])
        if not row["won"]:
            running = 0
        elif previous_date and puzzle_date == previous_date + timedelta(days=1):
            running += 1
        else:
            running = 1
        maximum = max(maximum, running)
        previous_date = puzzle_date
    return (running if rows and rows[-1]["won"] else 0), maximum


def get_stats(player_id: str) -> dict:
    player_id = _player_id(player_id)
    with database.connect() as connection:
        rows = connection.execute("SELECT mode, puzzle_date, won, attempts FROM game_results WHERE player_id = ? ORDER BY completed_at, id", (player_id,)).fetchall()
    games_played = len(rows)
    games_won = sum(bool(row["won"]) for row in rows)
    distribution = {str(attempt): 0 for attempt in range(1, 7)}
    for row in rows:
        if row["won"]:
            distribution[str(row["attempts"])] += 1
    daily_rows = sorted((row for row in rows if row["mode"] == "daily"), key=lambda row: row["puzzle_date"])
    current_streak, max_streak = _daily_streak(daily_rows)
    return {"games_played": games_played, "games_won": games_won, "win_percentage": round(games_won * 100 / games_played) if games_played else 0, "current_streak": current_streak, "max_streak": max_streak, "guess_distribution": distribution}


def record_result(player_id: str, mode: str, attempts: int, won: bool, puzzle_date: str | None, solution: str) -> dict:
    player_id = register_player(player_id)
    if mode not in {"daily", "unlimited"} or not isinstance(attempts, int) or not 1 <= attempts <= 6:
        raise ValueError("invalid game result")
    solution = normalize_guess(solution)
    if len(solution) != 5:
        raise ValueError("invalid solution")
    if mode == "daily":
        if not puzzle_date:
            raise ValueError("daily results require a puzzle date")
        if solution != get_daily_solution(date.fromisoformat(puzzle_date)):
            raise ValueError("daily solution does not match the server puzzle")
    else:
        puzzle_date = None
    with database.connect() as connection:
        cursor = connection.execute("INSERT INTO game_results (player_id, mode, puzzle_date, solution_id, won, attempts, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(player_id, mode, puzzle_date) DO NOTHING", (player_id, mode, puzzle_date, solution, int(won), attempts, database.now_iso()))
        recorded = cursor.rowcount > 0
    return {"recorded": recorded, "stats": get_stats(player_id)}
