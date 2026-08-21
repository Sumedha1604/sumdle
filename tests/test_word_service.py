from datetime import date

from backend import word_service


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
