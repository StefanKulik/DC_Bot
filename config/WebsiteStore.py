from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


DEFAULT_SITE_DESCRIPTION = "Diese Inhalte werden vom Discord-Bot verwaltet."
DEFAULT_ACCENT_COLOR = "#1f7aec"
CLEAR_TOKENS = {"-", "none", "clear", "leer"}

WEBSITE_SCHEMA_STATEMENTS = [
    "CREATE SCHEMA IF NOT EXISTS discord",
    """
    CREATE TABLE IF NOT EXISTS discord.website_settings (
        guild_id BIGINT PRIMARY KEY,
        site_name TEXT NOT NULL,
        site_description TEXT NOT NULL,
        invite_url TEXT,
        accent_color TEXT NOT NULL DEFAULT '#1f7aec',
        updated_by BIGINT,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS discord.website_entries (
        entry_id BIGSERIAL PRIMARY KEY,
        guild_id BIGINT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'Allgemein',
        link_url TEXT,
        image_url TEXT,
        is_published BOOLEAN NOT NULL DEFAULT TRUE,
        created_by BIGINT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_website_entries_guild_created_at
    ON discord.website_entries (guild_id, created_at DESC)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_website_entries_guild_published
    ON discord.website_entries (guild_id, is_published)
    """,
]


async def ensure_website_schema(executor: Any) -> None:
    for statement in WEBSITE_SCHEMA_STATEMENTS:
        await executor.execute(statement)


def normalize_clearable_text(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    if stripped.lower() in CLEAR_TOKENS:
        return None

    return stripped


def validate_hex_color(value: str | None) -> str | None:
    normalized = normalize_clearable_text(value)
    if normalized is None:
        return None

    if len(normalized) != 7 or not normalized.startswith("#"):
        raise ValueError("Die Farbe muss im Format #RRGGBB angegeben werden.")

    hex_part = normalized[1:]
    if any(character not in "0123456789abcdefABCDEF" for character in hex_part):
        raise ValueError("Die Farbe muss im Format #RRGGBB angegeben werden.")

    return normalized.lower()


def validate_optional_url(value: str | None) -> str | None:
    normalized = normalize_clearable_text(value)
    if normalized is None:
        return None

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Bitte eine gueltige URL mit http:// oder https:// angeben.")

    return normalized
