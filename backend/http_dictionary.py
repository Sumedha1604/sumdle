"""Keyless HTTP dictionary validation for deployed Sumdle instances."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import get_settings
from .mcp_client import McpUnavailableError

logger = logging.getLogger(__name__)


async def get_word_definition(word: str) -> dict[str, Any] | None:
    """Return a normalized definition, None for a confirmed miss, or raise if unavailable."""
    settings = get_settings()
    if not settings.dictionary_http_url:
        raise McpUnavailableError("HTTP dictionary is disabled")
    url = f"{settings.dictionary_http_url.rstrip('/')}/{word}"
    try:
        async with httpx.AsyncClient(timeout=settings.dictionary_http_timeout_seconds) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
    except httpx.HTTPError as error:
        logger.info("HTTP dictionary unavailable for %s: %s", word, error)
        raise McpUnavailableError("HTTP dictionary lookup failed") from error
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        logger.info("HTTP dictionary returned %s for %s", response.status_code, word)
        raise McpUnavailableError("HTTP dictionary lookup failed")
    try:
        payload = response.json()
    except ValueError as error:
        raise McpUnavailableError("HTTP dictionary returned invalid JSON") from error
    if not isinstance(payload, list) or not payload:
        raise McpUnavailableError("HTTP dictionary returned an unexpected response")
    entry = payload[0]
    if not isinstance(entry, dict) or not entry.get("meanings"):
        return None
    definitions = []
    examples = []
    for meaning in entry.get("meanings", []):
        if not isinstance(meaning, dict):
            continue
        for item in meaning.get("definitions", []):
            if isinstance(item, dict) and item.get("definition"):
                definitions.append({"part_of_speech": meaning.get("partOfSpeech"), "definition": str(item["definition"])})
                if item.get("example"):
                    examples.append(str(item["example"]))
    return {"word": word, "definitions": definitions, "examples": examples} if definitions else None
