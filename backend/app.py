"""HTTP interface for the Sumdle word engine."""

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI

from .mcp_client import McpUnavailableError
from .database import initialize_database
from .seed import seed_solutions
from .word_service import get_word_definition, validate_with_fallback


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    seed_solutions()
    yield


app = FastAPI(title="Sumdle word engine", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/words/validate/{word}")
async def validate_word(word: str) -> dict[str, str | bool | None]:
    return await validate_with_fallback(word)


@app.get("/api/words/{word}/lookup")
async def lookup_word(word: str) -> dict[str, str | bool]:
    return await validate_with_fallback(word)


@app.get("/api/words/{word}/definition")
async def word_definition(word: str) -> dict:
    normalized = word.strip().lower()
    try:
        definition = await get_word_definition(normalized)
    except McpUnavailableError:
        return {"word": normalized, "found": False, "source": "unavailable", "reason": "dictionary_lookup_unavailable"}
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
