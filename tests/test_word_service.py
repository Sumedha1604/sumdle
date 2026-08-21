from datetime import date
import asyncio

from backend import word_service
from backend.mcp_client import McpConfig, McpDictionaryClient


def test_valid_guess_and_normalization():
    assert word_service.is_valid_guess("crane")
    assert word_service.is_valid_guess("CRANE")
    assert word_service.is_valid_guess("  crane  ")


def test_invalid_and_nonalphabetic_guesses():
    assert not word_service.is_valid_guess("zzzzz")
    assert not word_service.is_valid_guess("cr4ne")
    assert not word_service.is_valid_guess("four")


def test_daily_solution_is_stable_and_is_a_solution():
    puzzle_date = date(2026, 8, 21)
    assert word_service.get_daily_solution(puzzle_date) == word_service.get_daily_solution(puzzle_date)
    assert word_service.get_daily_solution(puzzle_date) in word_service.SOLUTION_SET


def test_different_dates_are_deterministic():
    first = word_service.get_daily_solution(date(2026, 8, 21))
    second = word_service.get_daily_solution(date(2026, 8, 22))
    assert first == word_service.get_daily_solution(date(2026, 8, 21))
    assert second == word_service.get_daily_solution(date(2026, 8, 22))


def test_random_solution_and_exclusion():
    excluded = set(word_service.SOLUTIONS[:-1])
    assert word_service.get_random_solution(excluded) == word_service.SOLUTIONS[-1]
    assert word_service.get_random_solution() in word_service.SOLUTION_SET


def test_banks_are_well_formed_and_solutions_are_accepted():
    assert len(word_service.SOLUTIONS) == len(set(word_service.SOLUTIONS))
    assert len(word_service.VALID_GUESSES) == len(set(word_service.VALID_GUESSES))
    assert word_service.SOLUTION_SET <= word_service.VALID_GUESS_SET
    for bank in (word_service.SOLUTIONS, word_service.VALID_GUESSES):
        assert all(word.isalpha() and word.islower() and len(word) == 5 for word in bank)


def test_validate_with_fallback_short_circuits_local_words(monkeypatch):
    async def unexpected_lookup(word):
        raise AssertionError("MCP should not be used for local words")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unexpected_lookup)
    assert asyncio.run(word_service.validate_with_fallback("CRANE")) == {
        "word": "crane", "valid": True, "source": "local"
    }


def test_validate_with_fallback_accepts_mcp_definition(monkeypatch):
    async def mcp_lookup(word):
        assert word == "fiver"
        return {"word": word, "definitions": [{"definition": "A group of five."}], "examples": []}

    monkeypatch.setattr(word_service, "get_mcp_word_definition", mcp_lookup)
    assert asyncio.run(word_service.validate_with_fallback("fiver")) == {
        "word": "fiver", "valid": True, "source": "mcp"
    }


def test_validate_with_fallback_rejects_invalid_before_mcp(monkeypatch):
    async def unexpected_lookup(word):
        raise AssertionError("invalid inputs should not use MCP")

    monkeypatch.setattr(word_service, "get_mcp_word_definition", unexpected_lookup)
    assert asyncio.run(word_service.validate_with_fallback("four")) == {
        "word": "four", "valid": False, "source": "invalid"
    }


def test_mcp_client_caches_mocked_lookup(monkeypatch):
    client = McpDictionaryClient(McpConfig(command="mock-server"))
    calls = 0

    async def mocked_call(word):
        nonlocal calls
        calls += 1
        return {"word": word, "definitions": [{"definition": "A test word."}], "examples": []}

    monkeypatch.setattr(client, "_call_definition", mocked_call)
    first = asyncio.run(client.lookup_word_via_mcp("FIVER"))
    second = asyncio.run(client.lookup_word_via_mcp("fiver"))
    assert first == second
    assert calls == 1
