import asyncio
from datetime import date, datetime, timedelta

import pytest

from backend import database, game_service, player_stats, word_service
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
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "")
    return path


def test_database_initialization_is_repeatable(temporary_database):
    database.initialize_database()
    database.initialize_database()
    with database.connect() as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"solutions", "word_validation_cache", "players", "game_results"} <= tables


def test_player_results_stats_and_daily_streaks(temporary_database):
    player = "b6f7d24b-cf06-49a3-a245-a11cb201cdda"
    assert player_stats.register_player(player) == player
    assert player_stats.register_player(player) == player
    assert player_stats.get_stats(player)["games_played"] == 0
    first = date(2026, 8, 20)
    for offset, won, attempts in ((0, True, 2), (1, True, 3), (2, False, 6), (3, True, 4), (5, True, 1)):
        day = first + timedelta(days=offset)
        result = player_stats.record_result(player, "daily", attempts, won, day.isoformat(), word_service.get_daily_solution(day))
        assert result["recorded"]
    stats = player_stats.get_stats(player)
    assert stats == {"games_played": 5, "games_won": 4, "win_percentage": 80, "current_streak": 1, "max_streak": 2, "guess_distribution": {"1": 1, "2": 1, "3": 1, "4": 1, "5": 0, "6": 0}}


def test_unlimited_and_duplicate_daily_results(temporary_database):
    player = "6e349c1e-e299-4b8f-af1b-7c0f87d41f30"
    day = date(2026, 8, 22)
    solution = word_service.get_daily_solution(day)
    assert player_stats.record_result(player, "daily", 2, True, day.isoformat(), solution)["recorded"]
    assert not player_stats.record_result(player, "daily", 2, True, day.isoformat(), solution)["recorded"]
    assert player_stats.record_result(player, "unlimited", 6, False, None, "apple")["recorded"]
    stats = player_stats.get_stats(player)
    assert stats["games_played"] == 2 and stats["games_won"] == 1
    assert stats["current_streak"] == stats["max_streak"] == 1


def test_server_game_sessions_are_authoritative(temporary_database, monkeypatch):
    player = "6e349c1e-e299-4b8f-af1b-7c0f87d41f31"

    async def valid_guess(word):
        return {"word": word, "valid": True, "source": "cache"}

    monkeypatch.setattr(game_service, "validate_with_fallback", valid_guess)
    game = game_service.start_game(player, "unlimited")
    assert "solution" not in game and game["status"] == "playing" and game["attempts"] == 0
    with database.connect() as connection:
        solution = connection.execute("SELECT solution FROM game_sessions WHERE id = ?", (game["game_id"],)).fetchone()["solution"]
    result = asyncio.run(game_service.submit_guess(game["game_id"], solution))
    assert result["status"] == "won" and result["attempts"] == 1 and result["solution"] == solution
    assert result["guesses"][0]["result"] == ["correct"] * 5
    assert player_stats.get_stats(player)["games_won"] == 1
    with pytest.raises(ValueError):
        asyncio.run(game_service.submit_guess(game["game_id"], solution))


def test_sessions_count_only_valid_guesses_and_daily_resumes(temporary_database, monkeypatch):
    player = "6e349c1e-e299-4b8f-af1b-7c0f87d41f32"

    async def invalid_guess(word):
        return {"word": word, "valid": False, "source": "cache"}

    monkeypatch.setattr(game_service, "validate_with_fallback", invalid_guess)
    daily = game_service.start_game(player, "daily")
    invalid = asyncio.run(game_service.submit_guess(daily["game_id"], "zzzzz"))
    assert not invalid["accepted"] and invalid["attempts"] == 0
    assert game_service.start_game(player, "daily")["game_id"] == daily["game_id"]


def test_daily_session_includes_timezone_aware_next_reset(temporary_database):
    daily = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f51", "daily")
    reset_at = datetime.fromisoformat(daily["next_daily_reset_at"])
    assert reset_at.tzinfo is not None and reset_at.utcoffset() is not None
    unlimited = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f52", "unlimited")
    assert "next_daily_reset_at" not in unlimited


def test_duplicate_letters_and_six_attempt_loss(temporary_database, monkeypatch):
    assert game_service.evaluate_guess("poppy", "apple") == ["present", "absent", "correct", "absent", "absent"]

    async def valid_guess(word):
        return {"word": word, "valid": True, "source": "cache"}

    monkeypatch.setattr(game_service, "validate_with_fallback", valid_guess)
    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f33", "unlimited")
    with database.connect() as connection:
        connection.execute("UPDATE game_sessions SET solution = 'apple' WHERE id = ?", (game["game_id"],))
    for _ in range(6):
        result = asyncio.run(game_service.submit_guess(game["game_id"], "beach"))
    assert result["status"] == "lost" and result["attempts"] == 6 and result["solution"] == "apple"


def test_hints_persist_are_sanitized_and_definitions_wait_for_completion(temporary_database, monkeypatch):
    player = "6e349c1e-e299-4b8f-af1b-7c0f87d41f34"

    async def definition(word):
        return {"word": word, "phonetic": "ˈapəl", "definitions": [{"part_of_speech": "noun", "definition": "an apple is a round fruit"}], "examples": []}

    monkeypatch.setattr(game_service, "get_word_definition", definition)
    game = game_service.start_game(player, "unlimited")
    with database.connect() as connection:
        connection.execute("UPDATE game_sessions SET solution = 'apple' WHERE id = ?", (game["game_id"],))
    with pytest.raises(PermissionError):
        asyncio.run(game_service.get_definition(game["game_id"]))
    first = asyncio.run(game_service.get_hint(game["game_id"], 1))
    second = asyncio.run(game_service.get_hint(game["game_id"], 2))
    assert first["hint_count"] == 1 and "apple" not in first["hint"].lower()
    assert second["hint_count"] == 2 and "apple" not in second["hint"].lower()
    assert game_service.get_game(game["game_id"])["hint_count"] == 2
    with pytest.raises(ValueError):
        asyncio.run(game_service.get_hint(game["game_id"], 1))

    async def valid_guess(word):
        return {"word": word, "valid": True, "source": "cache"}

    monkeypatch.setattr(game_service, "validate_with_fallback", valid_guess)
    asyncio.run(game_service.submit_guess(game["game_id"], "apple"))
    assert asyncio.run(game_service.get_definition(game["game_id"]))["definition"] == "an apple is a round fruit"


def test_daily_hints_resume_with_the_same_session_and_reject_completed_games(temporary_database, monkeypatch):
    player = "6e349c1e-e299-4b8f-af1b-7c0f87d41f53"

    async def definition(word):
        return {"word": word, "definitions": [{"part_of_speech": "noun", "definition": "a small test word"}], "examples": []}

    async def valid_guess(word):
        return {"word": word, "valid": True, "source": "cache"}

    monkeypatch.setattr(game_service, "get_word_definition", definition)
    monkeypatch.setattr(game_service, "validate_with_fallback", valid_guess)
    daily = game_service.start_game(player, "daily")

    assert daily["mode"] == "daily"
    assert daily["status"] == "playing"
    assert daily["hint_count"] == 0
    assert asyncio.run(game_service.get_hint(daily["game_id"], 1))["hint_count"] == 1

    resumed = game_service.start_game(player, "daily")
    assert resumed["game_id"] == daily["game_id"]
    assert resumed["hint_count"] == 1
    assert asyncio.run(game_service.get_hint(resumed["game_id"], 2))["hint_count"] == 2

    with database.connect() as connection:
        connection.execute("UPDATE game_sessions SET status = 'won' WHERE id = ?", (daily["game_id"],))
    with pytest.raises(ValueError, match="already complete"):
        asyncio.run(game_service.get_hint(daily["game_id"], 1))


def test_second_hint_preserves_a_long_definition_without_truncation(temporary_database, monkeypatch):
    long_definition = "a carefully written definition that continues well beyond one hundred and fifty characters so players can read every useful detail rather than seeing a sentence end unexpectedly in the middle of a word"

    async def definition(word):
        return {"word": word, "definitions": [{"part_of_speech": "noun", "definition": long_definition}], "examples": []}

    monkeypatch.setattr(game_service, "get_word_definition", definition)
    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f54", "unlimited")
    result = asyncio.run(game_service.get_hint(game["game_id"], 2))

    assert result["hint"] == long_definition
    assert len(result["hint"]) > 150


def test_hint_and_definition_handle_dictionary_outage(temporary_database, monkeypatch):
    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f35", "unlimited")

    async def unavailable(word):
        raise McpUnavailableError("offline")

    monkeypatch.setattr(game_service, "get_word_definition", unavailable)
    assert not asyncio.run(game_service.get_hint(game["game_id"], 1))["available"]


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


def test_http_dictionary_results_are_cached(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")

    async def external(word):
        assert word == "stare"
        return {"word": word, "definitions": [{"definition": "to look fixedly"}], "examples": []}

    monkeypatch.setattr(word_service, "get_http_word_definition", external)
    assert asyncio.run(word_service.validate_with_fallback("STARE")) == {"word": "stare", "valid": True, "source": "http"}
    assert asyncio.run(word_service.validate_with_fallback("stare")) == {"word": "stare", "valid": True, "source": "cache"}


def test_http_invalid_and_unavailable_results(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")

    async def invalid(word):
        return None

    monkeypatch.setattr(word_service, "get_http_word_definition", invalid)
    assert asyncio.run(word_service.validate_with_fallback("qzqzx")) == {"word": "qzqzx", "valid": False, "source": "http"}
    assert asyncio.run(word_service.validate_with_fallback("qzqzx")) == {"word": "qzqzx", "valid": False, "source": "cache"}

    async def unavailable(word):
        raise McpUnavailableError("timeout")

    monkeypatch.setattr(word_service, "get_http_word_definition", unavailable)
    assert asyncio.run(word_service.validate_with_fallback("stork"))["valid"] is None
    with database.connect() as connection:
        assert connection.execute("SELECT 1 FROM word_validation_cache WHERE word = 'stork'").fetchone() is None


def test_cached_valid_word_missing_metadata_falls_back_to_http_and_is_returned(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")
    calls = 0

    async def external(word):
        nonlocal calls
        calls += 1
        assert word == "plant"
        return {"word": word, "definitions": [{"part_of_speech": "noun", "definition": "a living organism of the kind exemplified by trees"}], "examples": [], "phonetic": "plɑːnt"}

    monkeypatch.setattr(word_service, "get_http_word_definition", external)

    seed_solutions()
    with database.connect() as connection:
        seeded = connection.execute("SELECT valid, definition FROM word_validation_cache WHERE word = 'plant'").fetchone()
    assert seeded["valid"] == 1 and seeded["definition"] is None

    definition = asyncio.run(word_service.get_word_definition("plant"))
    assert calls == 1
    assert definition["definitions"][0]["definition"] == "a living organism of the kind exemplified by trees"
    assert definition["phonetic"] == "plɑːnt"


def test_enriched_metadata_is_persisted_and_reused_without_another_http_call(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")
    calls = 0

    async def external(word):
        nonlocal calls
        calls += 1
        return {"word": word, "definitions": [{"part_of_speech": "noun", "definition": "a living organism of the kind exemplified by trees"}], "examples": []}

    monkeypatch.setattr(word_service, "get_http_word_definition", external)

    first = asyncio.run(word_service.get_word_definition("plant"))
    with database.connect() as connection:
        row = connection.execute("SELECT valid, definition FROM word_validation_cache WHERE word = 'plant'").fetchone()
    assert row["valid"] == 1 and "living organism" in row["definition"]

    second = asyncio.run(word_service.get_word_definition("plant"))
    assert second == first
    assert calls == 1  # cache now serves the enriched row; no repeat HTTP call


def test_completed_game_definition_for_seeded_word_uses_dictionary_enrichment(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")

    async def valid_guess(word):
        return {"word": word, "valid": True, "source": "cache"}

    monkeypatch.setattr(game_service, "validate_with_fallback", valid_guess)

    async def external(word):
        assert word == "plant"
        return {"word": word, "definitions": [{"part_of_speech": "noun", "definition": "a living organism of the kind exemplified by trees"}], "examples": [], "phonetic": "plɑːnt"}

    monkeypatch.setattr(word_service, "get_http_word_definition", external)

    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f36", "unlimited")
    with database.connect() as connection:
        connection.execute("UPDATE game_sessions SET solution = 'plant' WHERE id = ?", (game["game_id"],))
    asyncio.run(game_service.submit_guess(game["game_id"], "plant"))

    result = asyncio.run(game_service.get_definition(game["game_id"]))
    assert result == {
        "word": "plant",
        "available": True,
        "part_of_speech": "noun",
        "definition": "a living organism of the kind exemplified by trees",
        "phonetic": "plɑːnt",
    }


def test_definition_dictionary_outage_returns_graceful_unavailable_response(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")

    async def valid_guess(word):
        return {"word": word, "valid": True, "source": "cache"}

    monkeypatch.setattr(game_service, "validate_with_fallback", valid_guess)

    async def unavailable(word):
        raise McpUnavailableError("offline")

    monkeypatch.setattr(word_service, "get_http_word_definition", unavailable)

    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f37", "unlimited")
    with database.connect() as connection:
        connection.execute("UPDATE game_sessions SET solution = 'plant' WHERE id = ?", (game["game_id"],))
    asyncio.run(game_service.submit_guess(game["game_id"], "plant"))

    result = asyncio.run(game_service.get_definition(game["game_id"]))
    assert result == {"word": "plant", "available": False}


def test_definition_remains_inaccessible_while_game_is_playing(temporary_database):
    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f38", "unlimited")
    with pytest.raises(PermissionError):
        asyncio.run(game_service.get_definition(game["game_id"]))


def test_hint_enrichment_works_for_seeded_words_missing_metadata(temporary_database, monkeypatch):
    monkeypatch.setenv("SUMDLE_DICTIONARY_HTTP_URL", "https://dictionary.example")

    async def external(word):
        assert word == "plant"
        return {"word": word, "definitions": [{"part_of_speech": "noun", "definition": "a living organism of the kind exemplified by trees"}], "examples": []}

    monkeypatch.setattr(word_service, "get_http_word_definition", external)

    game = game_service.start_game("6e349c1e-e299-4b8f-af1b-7c0f87d41f39", "unlimited")
    with database.connect() as connection:
        connection.execute("UPDATE game_sessions SET solution = 'plant' WHERE id = ?", (game["game_id"],))
    hint = asyncio.run(game_service.get_hint(game["game_id"], 1))
    assert hint == {"hint_count": 1, "hint": "this word is commonly used as a noun", "available": True}
