"""HTTP interface for the Sumdle word engine."""

from datetime import date

from fastapi import FastAPI

from .word_service import is_valid_guess

app = FastAPI(title="Sumdle word engine")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/words/validate/{word}")
def validate_word(word: str) -> dict[str, str | bool]:
    normalized = word.strip().lower()
    return {"word": normalized, "valid": is_valid_guess(word)}


@app.get("/api/puzzle/daily")
def daily_puzzle() -> dict[str, str]:
    # Do not return the answer: client-side answer evaluation remains a known
    # limitation of the current React game until a server-side protocol is added.
    return {"mode": "daily", "date": date.today().isoformat()}


@app.get("/api/puzzle/random")
def random_puzzle() -> dict[str, str]:
    return {"mode": "random"}
