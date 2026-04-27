from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.WebsiteStore import DEFAULT_ACCENT_COLOR, ensure_website_schema


OUTPUT_PATH = ROOT / "docs" / "data" / "site-data.json"
ENV_PATH = ROOT / "config" / ".env"


def build_payload(
    *,
    generated_at: str,
    guilds: list[dict],
) -> dict:
    project_name = os.getenv("SITE_PROJECT_NAME", "Discord Bot Showcase")
    project_tagline = os.getenv("SITE_PROJECT_TAGLINE", "Inhalte aus der Bot-Datenbank")
    entry_count = sum(len(guild["entries"]) for guild in guilds)
    return {
        "generatedAt": generated_at,
        "project": {
            "name": project_name,
            "tagline": project_tagline,
            "source": "discord.website_entries",
        },
        "totals": {
            "guildCount": len(guilds),
            "entryCount": entry_count,
        },
        "guilds": guilds,
    }


async def fetch_data() -> dict:
    database_url = os.getenv("DATABASE_URL")
    generated_at = datetime.now(timezone.utc).isoformat()
    if not database_url or database_url == "unknown":
        return build_payload(generated_at=generated_at, guilds=[])

    connection = None
    try:
        connection = await asyncpg.connect(dsn=database_url, server_settings={"search_path": "discord"})
        await ensure_website_schema(connection)

        settings_rows = await connection.fetch(
            """
            SELECT guild_id, site_name, site_description, invite_url, accent_color, updated_at
            FROM discord.website_settings
            ORDER BY site_name ASC
            """
        )
        entry_rows = await connection.fetch(
            """
            SELECT
                entry_id,
                guild_id,
                title,
                description,
                category,
                link_url,
                image_url,
                created_at,
                updated_at
            FROM discord.website_entries
            WHERE is_published = TRUE
            ORDER BY guild_id ASC, created_at DESC
            """
        )
    except Exception as exc:
        print(f"Website export failed: {type(exc).__name__}: {exc}")
        return build_payload(generated_at=generated_at, guilds=[])
    finally:
        if connection is not None:
            await connection.close()

    guild_map: dict[int, dict] = {}
    for row in settings_rows:
        guild_map[int(row["guild_id"])] = {
            "guildId": str(row["guild_id"]),
            "name": row["site_name"],
            "description": row["site_description"],
            "inviteUrl": row["invite_url"] or os.getenv("DISCORD_SERVER_INVITE"),
            "accentColor": row["accent_color"] or DEFAULT_ACCENT_COLOR,
            "updatedAt": row["updated_at"].isoformat(),
            "entries": [],
        }

    entry_groups: dict[int, list[dict]] = defaultdict(list)
    for row in entry_rows:
        guild_id = int(row["guild_id"])
        entry_groups[guild_id].append(
            {
                "id": int(row["entry_id"]),
                "title": row["title"],
                "description": row["description"],
                "category": row["category"],
                "linkUrl": row["link_url"],
                "imageUrl": row["image_url"],
                "createdAt": row["created_at"].isoformat(),
                "updatedAt": row["updated_at"].isoformat(),
            }
        )

    for guild_id, entries in entry_groups.items():
        guild = guild_map.get(guild_id)
        if guild is None:
            guild = {
                "guildId": str(guild_id),
                "name": f"Discord Server {guild_id}",
                "description": "Automatisch exportierte Inhalte",
                "inviteUrl": os.getenv("DISCORD_SERVER_INVITE"),
                "accentColor": DEFAULT_ACCENT_COLOR,
                "updatedAt": generated_at,
                "entries": [],
            }
            guild_map[guild_id] = guild
        guild["entries"] = entries

    guilds = [guild for guild in guild_map.values() if guild["entries"]]
    guilds.sort(key=lambda guild: guild["name"].lower())
    return build_payload(generated_at=generated_at, guilds=guilds)


async def main() -> None:
    load_dotenv(ENV_PATH)
    payload = await fetch_data()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Website data exported to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
