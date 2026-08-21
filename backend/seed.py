"""Deliberately small, human-curated seed list for Sumdle answers."""

from __future__ import annotations

from pathlib import Path

from .database import connect, now_iso

CURATED_SOLUTIONS = (
    "apple", "beach", "bloom", "candy", "cloud", "coral", "dance", "dream", "eagle", "earth",
    "flame", "flora", "focus", "grape", "green", "happy", "heart", "honey", "house", "jolly",
    "juice", "lemon", "light", "lucky", "magic", "maple", "melon", "money", "music", "ocean",
    "paint", "peace", "peach", "pearl", "petal", "plant", "pride", "rainy", "river", "robin",
    "sandy", "shine", "smile", "snack", "solar", "sound", "spice", "starry", "stone", "storm",
    "sweet", "tiger", "toast", "trail", "unity", "vivid", "water", "whale", "world", "youth",
)

# A deliberately small offline baseline for normal gameplay. This is not a
# replacement for MCP's broader dictionary; it keeps a fresh production cache
# usable when the optional stdio dictionary cannot run on the host.
FALLBACK_VALID_GUESSES = (
    "adore", "apple", "beach", "bless", "bloom", "blush", "brave", "broom", "cabin", "candy",
    "charm", "cider", "cloud", "coral", "crisp", "dance", "daisy", "dream", "earth", "fairy",
    "feast", "flair", "flame", "flora", "focus", "fruit", "giddy", "gleam", "grace", "grape",
    "green", "happy", "heart", "honey", "house", "ivory", "jolly", "laugh", "lemon", "light",
    "lilac", "lucky", "magic", "mango", "maple", "melon", "mirth", "money", "mossy", "music",
    "ocean", "olive", "paint", "peace", "pearl", "petal", "piano", "piney", "plant", "plume",
    "poems", "poppy", "pride", "prism", "quiet", "rainy", "raven", "river", "roses", "sandy",
    "satin", "scent", "shine", "shiny", "smile", "snack", "solar", "sound", "spark", "spice",
    "starry", "stone", "storm", "sugar", "sunny", "sweet", "tiger", "toast", "trail", "tulip",
    "twirl", "unity", "vapor", "vines", "vivid", "water", "whale", "whisk", "windy", "wispy",
    "world", "young", "youth", "zesty",
)


def seed_solutions(database_path: Path | str | None = None) -> None:
    """Insert curated answers idempotently without overwriting existing data."""
    with connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO solutions (word, difficulty, active, created_at) VALUES (?, ?, 1, ?) ON CONFLICT(word) DO NOTHING",
            [(word, "standard", now_iso()) for word in CURATED_SOLUTIONS],
        )
        connection.executemany(
            """INSERT INTO word_validation_cache (word, valid, definition, checked_at)
               VALUES (?, 1, NULL, ?) ON CONFLICT(word) DO NOTHING""",
            [(word, now_iso()) for word in FALLBACK_VALID_GUESSES],
        )
