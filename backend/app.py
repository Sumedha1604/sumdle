"""HTTP interface for the Sumdle word engine."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .mcp_client import McpUnavailableError
from .database import initialize_database
from .config import get_settings
from .seed import seed_solutions
from .word_service import validate_with_fallback
from .player_stats import get_stats, register_player
from .game_service import get_game, start_game, submit_guess


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


class StartGamePayload(BaseModel):
    player_id: str


class GuessPayload(BaseModel):
    guess: str


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


@app.post("/api/games/daily")
def start_daily_game(payload: StartGamePayload) -> dict:
    try:
        return start_game(payload.player_id, "daily")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/games/unlimited")
def start_unlimited_game(payload: StartGamePayload) -> dict:
    try:
        return start_game(payload.player_id, "unlimited")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/games/{game_id}")
def game(game_id: str) -> dict:
    try:
        return get_game(game_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/games/{game_id}/guess")
async def guess(game_id: str, payload: GuessPayload) -> dict:
    try:
        return await submit_guess(game_id, payload.guess)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


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
