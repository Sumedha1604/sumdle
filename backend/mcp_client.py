"""Optional MCP dictionary client used to enrich Sumdle's local word bank.

The client deliberately hides MCP protocol objects from the rest of the
application.  Configure a local stdio MCP server with ``SUMDLE_MCP_COMMAND``
and, optionally, ``SUMDLE_MCP_ARGS`` (a JSON array), ``SUMDLE_MCP_CWD``, and
``SUMDLE_MCP_TIMEOUT_SECONDS``.  Leaving the command unset disables MCP.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from .config import get_settings

logger = logging.getLogger(__name__)


class McpUnavailableError(RuntimeError):
    """The optional dictionary service could not be reached."""


@dataclass(frozen=True)
class McpConfig:
    command: str | None
    args: tuple[str, ...] = ()
    cwd: str | None = None
    timeout_seconds: float = 3.0

    @classmethod
    def from_environment(cls) -> "McpConfig":
        settings = get_settings()
        return cls(settings.mcp_command, settings.mcp_args, settings.mcp_cwd, settings.mcp_timeout_seconds)


def _definition_from_text(word: str, text: str) -> dict[str, Any] | None:
    """Normalize the Word of the Day server's Markdown response."""
    text = text.strip()
    if not text or re.search(r"\b(not found|no definitions?|error)\b", text, re.I):
        return None
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    if isinstance(decoded, dict):
        return _normalize_definition(word, decoded)

    phonetic_match = re.search(r"\*\*Pronunciation:\*\*\s*(.+)", text, re.I)
    entries = re.findall(
        r"^\s*\d+\.\s+\*\*([^*]+)\*\*\s*\n\s*\d+\.\s+(.+?)(?=\n\s*\d+\.\s+\*\*|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    definitions = [
        {"part_of_speech": part.strip(), "definition": re.sub(r"\s+", " ", meaning).strip()}
        for part, meaning in entries
    ]
    examples = [match.strip() for match in re.findall(r"\*Example:\s*[\"']?(.+?)[\"']?\*", text)]
    if not definitions and not phonetic_match:
        return None
    result: dict[str, Any] = {"word": word, "definitions": definitions, "examples": examples}
    if phonetic_match:
        result["phonetic"] = phonetic_match.group(1).strip()
    return result


def _normalize_definition(word: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return a stable public definition shape from a structured response."""
    if payload.get("found") is False or payload.get("error"):
        return None
    result: dict[str, Any] = {"word": str(payload.get("word") or word).lower(), "definitions": [], "examples": []}
    for key in ("phonetic", "pronunciation"):
        if payload.get(key):
            result["phonetic"] = str(payload[key])
            break
    meanings = payload.get("meanings") or payload.get("definitions") or []
    if isinstance(meanings, str):
        meanings = [{"definition": meanings}]
    for meaning in meanings if isinstance(meanings, list) else []:
        if isinstance(meaning, str):
            result["definitions"].append({"definition": meaning})
            continue
        if not isinstance(meaning, dict):
            continue
        part = meaning.get("partOfSpeech") or meaning.get("part_of_speech")
        items = meaning.get("definitions") if isinstance(meaning.get("definitions"), list) else [meaning]
        for item in items:
            if not isinstance(item, dict) or not item.get("definition"):
                continue
            entry = {"definition": str(item["definition"])}
            if part:
                entry["part_of_speech"] = str(part)
            result["definitions"].append(entry)
            if item.get("example"):
                result["examples"].append(str(item["example"]))
    return result if result["definitions"] or result.get("phonetic") else None


class McpDictionaryClient:
    """A small, reusable stdio client for the configured dictionary server."""

    def __init__(self, config: McpConfig | None = None) -> None:
        self.config = config or McpConfig.from_environment()
        self._cache: dict[str, dict[str, Any] | None] = {}

    async def lookup_word_via_mcp(self, word: str) -> dict[str, Any] | None:
        normalized = word.strip().lower() if isinstance(word, str) else ""
        if not normalized:
            return None
        if normalized in self._cache:
            return self._cache[normalized]
        if not self.config.command:
            raise McpUnavailableError("MCP dictionary is not configured")
        try:
            result = await asyncio.wait_for(self._call_definition(normalized), self.config.timeout_seconds)
        except Exception as error:  # The external server must never break gameplay.
            logger.info("MCP dictionary lookup unavailable for %s: %s", normalized, error)
            raise McpUnavailableError("MCP dictionary lookup failed") from error
        self._cache[normalized] = result
        return result

    async def _call_definition(self, word: str) -> dict[str, Any] | None:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as error:  # Keeps local gameplay usable before optional dependency install.
            raise RuntimeError("MCP SDK is not installed") from error

        parameters = StdioServerParameters(command=self.config.command, args=list(self.config.args), cwd=self.config.cwd)
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                response = await session.call_tool("get_word_definition", {"word": word, "language": "en"})
        if getattr(response, "isError", False):
            return None
        content = getattr(response, "content", [])
        texts = [item.text for item in content if getattr(item, "text", None)]
        if not texts:
            return None
        # Prefer a structured payload when the server returns one, otherwise parse its text.
        return _definition_from_text(word, "\n".join(texts))


_default_client = McpDictionaryClient()


async def lookup_word_via_mcp(word: str) -> dict[str, Any] | None:
    """Look up a word via the configured MCP server."""
    return await _default_client.lookup_word_via_mcp(word)


async def get_word_definition(word: str) -> dict[str, Any] | None:
    """Public alias that returns only the normalized definition data."""
    return await lookup_word_via_mcp(word)
