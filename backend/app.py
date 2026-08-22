"""HTTP interface for the Sumdle word engine."""

from contextlib import asynccontextmanager
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .mcp_client import McpUnavailableError
from .database import initialize_database
from .config import get_settings
from .seed import seed_solutions
from .word_service import NoActiveSolutionsError, get_daily_solution, get_random_solution, validate_with_fallback
from .player_stats import get_stats, record_result, register_player


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    seed_solutions()
    yield


app = FastAPI(title="Sumdle word engine", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(get_settings().cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class PlayerIdentity(BaseModel):
    player_id: str


class GameResultPayload(BaseModel):
    player_id: str
    mode: str
    attempts: int
    won: bool
    puzzle_date: str | None = None
    solution: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/players")
def create_player(payload: PlayerIdentity) -> dict[str, str]:
    try:
        return {"player_id": register_player(payload.player_id)}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/players/{player_id}/stats")
def player_stats(player_id: str) -> dict:
    try:
        return get_stats(player_id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/game-results")
def create_game_result(payload: GameResultPayload) -> dict:
    try:
        return record_result(**payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


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
    """Return the server-calendar daily puzzle for the current client evaluator."""
    puzzle_date = date.today()
    try:
        solution = get_daily_solution(puzzle_date)
    except NoActiveSolutionsError as error:
        raise HTTPException(status_code=503, detail="No daily puzzle is available") from error
    # The React evaluator currently runs in the browser, so this is not a
    # security boundary. Move evaluation server-side before treating answers as secret.
    return {"mode": "daily", "date": puzzle_date.isoformat(), "puzzle_id": puzzle_date.isoformat(), "solution": solution}


@app.get("/api/puzzle/random")
def random_puzzle(exclude: str | None = None) -> dict[str, str]:
    try:
        solution = get_random_solution({exclude} if exclude else None)
    except NoActiveSolutionsError as error:
        raise HTTPException(status_code=503, detail="No random puzzle is available") from error
    return {"mode": "unlimited", "solution": solution}
