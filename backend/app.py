"""HTTP interface for the Sumdle word engine."""

from datetime import date

from fastapi import FastAPI

from .word_service import get_word_definition, is_valid_guess, validate_with_fallback

app = FastAPI(title="Sumdle word engine")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/words/validate/{word}")
def validate_word(word: str) -> dict[str, str | bool]:
    normalized = word.strip().lower()
    return {"word": normalized, "valid": is_valid_guess(word)}


@app.get("/api/words/{word}/lookup")
async def lookup_word(word: str) -> dict[str, str | bool]:
    return await validate_with_fallback(word)


@app.get("/api/words/{word}/definition")
async def word_definition(word: str) -> dict:
    normalized = word.strip().lower()
    definition = await get_word_definition(normalized)
    if definition is None:
        return {"word": normalized, "found": False, "source": "mcp"}
    return {**definition, "found": True, "source": "mcp"}


@app.get("/api/puzzle/daily")
def daily_puzzle() -> dict[str, str]:
    # Do not return the answer: client-side answer evaluation remains a known
    # limitation of the current React game until a server-side protocol is added.
    return {"mode": "daily", "date": date.today().isoformat()}


@app.get("/api/puzzle/random")
def random_puzzle() -> dict[str, str]:
    return {"mode": "random"}
