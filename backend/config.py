"""Environment-backed settings shared by Sumdle's backend services."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _origins(value: str | None) -> tuple[str, ...]:
    return tuple(origin.strip() for origin in (value or "http://localhost:5173").split(",") if origin.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    cors_origins: tuple[str, ...]
    mcp_command: str | None
    mcp_args: tuple[str, ...]
    mcp_cwd: str | None
    mcp_timeout_seconds: float


def get_settings() -> Settings:
    raw_args = os.getenv("SUMDLE_MCP_ARGS", "[]")
    try:
        decoded_args = json.loads(raw_args)
        mcp_args = tuple(str(item) for item in decoded_args) if isinstance(decoded_args, list) else ()
    except json.JSONDecodeError:
        logger.warning("SUMDLE_MCP_ARGS must be a JSON array; ignoring its value")
        mcp_args = ()
    try:
        timeout = max(float(os.getenv("SUMDLE_MCP_TIMEOUT_SECONDS", "3")), 0.1)
    except ValueError:
        timeout = 3.0
    return Settings(os.getenv("DATABASE_URL") or None, _origins(os.getenv("CORS_ORIGINS")), os.getenv("SUMDLE_MCP_COMMAND") or None, mcp_args, os.getenv("SUMDLE_MCP_CWD") or None, timeout)
