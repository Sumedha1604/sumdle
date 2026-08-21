import asyncio

import pytest

from backend import database, word_service
from backend.mcp_client import McpUnavailableError
from backend.seed import CURATED_SOLUTIONS, seed_solutions


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


def test_solution_service_uses_sqlite(temporary_database):
    assert word_service.solution_exists("APPLE")
    assert word_service.get_random_solution() in CURATED_SOLUTIONS
    assert set(word_service.get_all_active_solutions()) == set(CURATED_SOLUTIONS)


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


def test_cached_words_work_during_mcp_outage(temporary_database, monkeypatch):
    async def valid_word(word):
        return {"word": word, "definitions": [{"definition": "To advance."}], "examples": []}

    monkeypatch.setattr(word_service, "get_mcp_word_definition", valid_word)
    asyncio.run(word_service.validate_with_fallback("forge"))

    async def unavailable(word):
        raise McpUnavailableError("offline")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unavailable)
    assert asyncio.run(word_service.validate_with_fallback("FORGE")) == {"word": "forge", "valid": True, "source": "cache"}
