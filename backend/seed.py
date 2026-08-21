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


def seed_solutions(database_path: Path | str | None = None) -> None:
    """Insert curated answers idempotently without overwriting existing data."""
    with connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO solutions (word, difficulty, active, created_at) VALUES (?, ?, 1, ?) ON CONFLICT(word) DO NOTHING",
            [(word, "standard", now_iso()) for word in CURATED_SOLUTIONS],
        )
