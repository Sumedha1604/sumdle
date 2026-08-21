import asyncio
from datetime import date, timedelta

import pytest

from backend import database, word_service
from backend.word_service import NoActiveSolutionsError
from backend.mcp_client import McpUnavailableError
from backend.seed import CURATED_SOLUTIONS, FALLBACK_VALID_GUESSES, seed_solutions


class FakePsycopgCursor:
    def __init__(self):
        self.executemany_calls = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def executemany(self, query, parameter_sets):
        self.executemany_calls.append((query, parameter_sets))


class FakePsycopgConnection:
    def __init__(self):
        self.cursor_instance = FakePsycopgCursor()
        self.execute_calls = []
        self.commits = 0

    def execute(self, query, parameters):
        self.execute_calls.append((query, parameters))

    def cursor(self):
        return self.cursor_instance

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *args):
        if exc_type is None:
            self.commits += 1


def test_postgresql_adapter_uses_cursor_for_bulk_execution_and_commits():
    raw_connection = FakePsycopgConnection()
    connection = database.DatabaseConnection(raw_connection, "postgresql")
    values = [("apple",), ("beach",)]
    with connection:
        connection.execute("SELECT ?", ("word",))
        connection.executemany("INSERT INTO solutions (word) VALUES (?)", values)
    assert raw_connection.execute_calls == [("SELECT %s", ("word",))]
    assert raw_connection.cursor_instance.executemany_calls == [
        ("INSERT INTO solutions (word) VALUES (%s)", values)
    ]
    assert raw_connection.cursor_instance.closed
    assert raw_connection.commits == 1


@pytest.fixture
def temporary_database(tmp_path, monkeypatch):
    path = tmp_path / "sumdle.db"
    monkeypatch.setattr(database, "DATABASE_PATH", path)
    return path


def test_database_initialization_is_repeatable(temporary_database):
    database.initialize_database()
    database.initialize_database()
    with database.connect() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"solutions", "word_validation_cache"} <= tables


def test_seed_is_idempotent_and_unique(temporary_database):
    seed_solutions()
    seed_solutions()
    with database.connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM solutions").fetchone()[0]
    assert count == len(CURATED_SOLUTIONS)
    assert len(CURATED_SOLUTIONS) == len(set(CURATED_SOLUTIONS))
    with database.connect() as connection:
        cached_count = connection.execute("SELECT COUNT(*) FROM word_validation_cache WHERE valid = 1").fetchone()[0]
    assert cached_count == len(FALLBACK_VALID_GUESSES)


def test_solution_service_uses_sqlite(temporary_database):
    assert word_service.solution_exists("APPLE")
    assert word_service.get_random_solution() in CURATED_SOLUTIONS
    assert set(word_service.get_all_active_solutions()) == set(CURATED_SOLUTIONS)


def test_daily_solution_is_stable_and_uses_active_sorted_solutions(temporary_database):
    puzzle_date = date(2026, 8, 21)
    first = word_service.get_daily_solution(puzzle_date)
    assert first == word_service.get_daily_solution(puzzle_date)
    assert first in word_service.get_all_active_solutions()


def test_daily_selection_can_vary_between_dates(temporary_database):
    first = word_service.get_daily_solution(date(2026, 1, 1))
    assert any(word_service.get_daily_solution(date(2026, 1, 1) + timedelta(days=offset)) != first for offset in range(1, 30))


def test_random_solution_is_active_and_skips_exclusion_when_possible(temporary_database):
    solution = word_service.get_random_solution({"apple"})
    assert solution in word_service.get_all_active_solutions()
    assert solution != "apple"


def test_inactive_or_empty_solutions_are_never_selected(temporary_database):
    word_service.get_all_active_solutions()
    with database.connect() as connection:
        connection.execute("UPDATE solutions SET active = 0")
    assert word_service.get_all_active_solutions() == ()
    with pytest.raises(NoActiveSolutionsError):
        word_service.get_daily_solution(date(2026, 1, 1))
    with pytest.raises(NoActiveSolutionsError):
        word_service.get_random_solution()


def test_malformed_input_skips_mcp(temporary_database, monkeypatch):
    async def unexpected_lookup(word):
        raise AssertionError("MCP must not receive malformed guesses")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unexpected_lookup)
    assert asyncio.run(word_service.validate_with_fallback("app4e")) == {
        "word": "app4e", "valid": False, "source": "invalid"
    }


def test_mcp_result_is_persisted_and_later_uses_cache(temporary_database, monkeypatch):
    calls = 0

    async def mcp_lookup(word):
        nonlocal calls
        calls += 1
        return {"word": word, "definitions": [{"definition": "A group of five."}], "examples": []}

    monkeypatch.setattr(word_service, "get_mcp_word_definition", mcp_lookup)
    assert asyncio.run(word_service.validate_with_fallback("FIVER")) == {"word": "fiver", "valid": True, "source": "mcp"}
    assert asyncio.run(word_service.validate_with_fallback("fiver")) == {"word": "fiver", "valid": True, "source": "cache"}
    assert calls == 1
    with database.connect() as connection:
        row = connection.execute("SELECT valid, definition FROM word_validation_cache WHERE word = 'fiver'").fetchone()
    assert row["valid"] == 1 and "group of five" in row["definition"]
    assert not word_service.solution_exists("fiver")


def test_invalid_mcp_result_is_cached(temporary_database, monkeypatch):
    calls = 0

    async def missing_word(word):
        nonlocal calls
        calls += 1
        return None

    monkeypatch.setattr(word_service, "get_mcp_word_definition", missing_word)
    assert asyncio.run(word_service.validate_with_fallback("zzzzz")) == {"word": "zzzzz", "valid": False, "source": "mcp"}
    assert asyncio.run(word_service.validate_with_fallback("ZZZZZ")) == {"word": "zzzzz", "valid": False, "source": "cache"}
    assert calls == 1


def test_mcp_outage_is_unknown_and_not_cached(temporary_database, monkeypatch):
    async def unavailable(word):
        raise McpUnavailableError("offline")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unavailable)
    result = asyncio.run(word_service.validate_with_fallback("adieu"))
    assert result == {"word": "adieu", "valid": None, "source": "unavailable", "reason": "dictionary_lookup_unavailable"}
    with database.connect() as connection:
        assert connection.execute("SELECT 1 FROM word_validation_cache WHERE word = 'adieu'").fetchone() is None


def test_offline_baseline_accepts_common_guesses_when_mcp_is_unavailable(temporary_database, monkeypatch):
    async def unexpected_lookup(word):
        raise AssertionError("seeded fallback must not call MCP")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unexpected_lookup)
    assert asyncio.run(word_service.validate_with_fallback("BRAVE")) == {
        "word": "brave", "valid": True, "source": "cache"
    }


def test_cached_words_work_during_mcp_outage(temporary_database, monkeypatch):
    async def valid_word(word):
        return {"word": word, "definitions": [{"definition": "To advance."}], "examples": []}

    monkeypatch.setattr(word_service, "get_mcp_word_definition", valid_word)
    asyncio.run(word_service.validate_with_fallback("forge"))

    async def unavailable(word):
        raise McpUnavailableError("offline")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unavailable)
    assert asyncio.run(word_service.validate_with_fallback("FORGE")) == {"word": "forge", "valid": True, "source": "cache"}
