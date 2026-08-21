"""Build normalized Sumdle word banks from a trusted word-list source.

The included solution candidates are intentionally small and hand-curated.  The
accepted-guess list is derived from a supplied dictionary, so it can be
regenerated from a larger vetted open dataset without changing application code.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# Familiar, answer-worthy words. Keep editorial review here; do not treat every
# dictionary entry as a suitable puzzle answer.
SOLUTION_CANDIDATES = """
adobe agent algae amber angel apple apron arena argue aroma awake baker basil beach berry birch
blaze bloom blouse board bonus booth bound brave bread brick bride brush cable cabin canoe
caper carve cedar chain chair chalk charm cheer chess chest chief cider clear clerk cliff cloud
coast coral craft crane cream creek crisp crown dance dairy daisy delta diner dream dress drift
eager earth ember fairy faith feast field flame flair flora floor flood flour focus forge
frame fresh fruit fuzzy giant glass gleam globe grace grain grape grass green grove happy heart
honey hotel house ivory jelly jewel jolly judge lemon light lilac linen lucky lunch magic maple
march match melon metal minty model money mossy music needy night noble ocean olive onion
peach pearl petal piano piney pinky plumb plume poems poppy pride prism quiet radio raven river
robin roses royal ruler satin scent shade shine shiny shore short skunk smile solar sound spark
spice spire splash spoon sport stage steam stone storm sugar sunny sweet table tango teach thief
tidal tiger toast token tonic torch trail train treat trend tulip twirl vapor vivid water weary
whale wheat whisk white windy wings world young youth zesty
""".split()


def normalize_word(word: str) -> str:
    """Trim and lowercase one candidate word."""
    return word.strip().lower()


def is_five_letter_word(word: str) -> bool:
    """Return whether a normalized word is exactly five ASCII letters."""
    return len(word) == 5 and word.isascii() and word.isalpha()


def normalize_words(words: Iterable[str]) -> list[str]:
    """Normalize, filter, deduplicate, and sort raw word entries."""
    return sorted({normalized for raw in words if is_five_letter_word(normalized := normalize_word(raw))})


def load_raw_words(path: str | Path) -> list[str]:
    """Load one raw word per line, accepting plain-text dictionary files."""
    return Path(path).read_text(encoding="utf-8").splitlines()


def generate_valid_guesses(raw_words: Iterable[str], solutions: Iterable[str] = ()) -> list[str]:
    """Produce the accepted bank, always including every solution."""
    return normalize_words([*raw_words, *solutions])


def generate_solutions(candidates: Iterable[str] = SOLUTION_CANDIDATES) -> list[str]:
    """Produce the reviewed answer bank from editorial candidates."""
    return normalize_words(candidates)


def write_word_banks(raw_words: Iterable[str], output_dir: str | Path = DATA_DIR) -> tuple[list[str], list[str]]:
    """Generate and write ``solutions.json`` and ``valid_guesses.json``."""
    solutions = generate_solutions()
    valid_guesses = generate_valid_guesses(raw_words, solutions)
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "solutions.json").write_text(json.dumps(solutions, indent=2) + "\n", encoding="utf-8")
    (destination / "valid_guesses.json").write_text(json.dumps(valid_guesses, indent=2) + "\n", encoding="utf-8")
    return solutions, valid_guesses


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Sumdle word banks from a newline-delimited dictionary.")
    parser.add_argument("raw_word_file", help="Path to a trusted raw dictionary file")
    parser.add_argument("--output-dir", default=DATA_DIR, type=Path)
    args = parser.parse_args()
    solutions, guesses = write_word_banks(load_raw_words(args.raw_word_file), args.output_dir)
    print(f"Wrote {len(solutions)} solutions and {len(guesses)} accepted guesses to {args.output_dir}")


if __name__ == "__main__":
    main()
