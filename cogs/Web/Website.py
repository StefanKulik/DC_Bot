from __future__ import annotations

import asyncpg
import discord
from discord import app_commands
from discord.ext import commands

from config.WebsiteStore import (
    DEFAULT_ACCENT_COLOR,
    DEFAULT_SITE_DESCRIPTION,
    ensure_website_schema,
    validate_hex_color,
    validate_optional_url,
)
from config.Util import send_interaction_message


LIST_LIMIT_DEFAULT = 5
LIST_LIMIT_MAX = 15


class Website(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        db = getattr(self.bot, "db", None)
        if db is None:
            return

        try:
            await ensure_website_schema(db)
        except Exception as exc:
            print(f"Website schema setup failed: {type(exc).__name__}: {exc}")

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await send_interaction_message(
                interaction,
                content="Dafuer brauchst du die Berechtigung 'Server verwalten'.",
                ephemeral=True,
            )
            return
        raise error

    async def ensure_settings_row(self, guild: discord.Guild, user_id: int) -> asyncpg.Record | None:
        db = getattr(self.bot, "db", None)
        if db is None:
            return None

        await db.execute(
            """
            INSERT INTO discord.website_settings(guild_id, site_name, site_description, accent_color, updated_by)
            VALUES($1, $2, $3, $4, $5)
            ON CONFLICT (guild_id) DO NOTHING
            """,
            guild.id,
            guild.name,
            DEFAULT_SITE_DESCRIPTION,
            DEFAULT_ACCENT_COLOR,
            user_id,
        )
        return await db.fetchrow(
            """
            SELECT guild_id, site_name, site_description, invite_url, accent_color, updated_at
            FROM discord.website_settings
            WHERE guild_id = $1
            """,
            guild.id,
        )

    async def get_db_or_error(self, interaction: discord.Interaction):
        db = getattr(self.bot, "db", None)
        if db is None:
            await send_interaction_message(
                interaction,
                content="Die Datenbank ist aktuell nicht verfuegbar.",
                ephemeral=True,
            )
            return None
        return db

    @app_commands.command(name="website_config", description="Konfiguriert die GitHub-Pages-Ausgabe fuer diesen Server")
    @app_commands.describe(
        site_name="Titel auf der Webseite",
        site_description="Kurzbeschreibung fuer die Webseite",
        invite_url="Discord-Einladungslink oder '-' zum Leeren",
        accent_color="Akzentfarbe im Format #RRGGBB",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def website_config(
        self,
        interaction: discord.Interaction,
        site_name: str | None = None,
        site_description: str | None = None,
        invite_url: str | None = None,
        accent_color: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await send_interaction_message(
                interaction,
                content="Dieser Befehl funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        db = await self.get_db_or_error(interaction)
        if db is None:
            return

        try:
            normalized_invite_url = validate_optional_url(invite_url) if invite_url is not None else None
            normalized_color = validate_hex_color(accent_color) if accent_color is not None else None
        except ValueError as exc:
            await send_interaction_message(interaction, content=str(exc), ephemeral=True)
            return

        current = await self.ensure_settings_row(interaction.guild, interaction.user.id)
        if current is None:
            await send_interaction_message(
                interaction,
                content="Die Web-Einstellungen konnten nicht geladen werden.",
                ephemeral=True,
            )
            return

        next_site_name = (site_name or current["site_name"]).strip()
        next_description = (site_description or current["site_description"]).strip()
        next_invite_url = current["invite_url"] if invite_url is None else normalized_invite_url
        next_color = current["accent_color"] if normalized_color is None else normalized_color

        await db.execute(
            """
            INSERT INTO discord.website_settings(
                guild_id,
                site_name,
                site_description,
                invite_url,
                accent_color,
                updated_by,
                updated_at
            )
            VALUES($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (guild_id) DO UPDATE SET
                site_name = EXCLUDED.site_name,
                site_description = EXCLUDED.site_description,
                invite_url = EXCLUDED.invite_url,
                accent_color = EXCLUDED.accent_color,
                updated_by = EXCLUDED.updated_by,
                updated_at = NOW()
            """,
            interaction.guild.id,
            next_site_name,
            next_description,
            next_invite_url,
            next_color,
            interaction.user.id,
        )

        embed = discord.Embed(
            title="Web-Konfiguration gespeichert",
            description="Diese Werte werden beim naechsten Export fuer GitHub Pages verwendet.",
            colour=discord.Colour.from_str(next_color),
        )
        embed.add_field(name="Titel", value=next_site_name, inline=False)
        embed.add_field(name="Beschreibung", value=next_description, inline=False)
        embed.add_field(name="Invite", value=next_invite_url or "Nicht gesetzt", inline=False)
        embed.add_field(name="Akzentfarbe", value=next_color, inline=False)
        await send_interaction_message(interaction, embed=embed, ephemeral=True)

    @app_commands.command(name="website_add", description="Legt einen neuen Webseite-Eintrag an")
    @app_commands.describe(
        title="Titel des Eintrags",
        description="Beschreibung des Eintrags",
        category="Kategorie auf der Webseite",
        link_url="Optionale externe URL",
        image_url="Optionale Bild-URL",
        published="Soll der Eintrag sofort auf der Webseite sichtbar sein?",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def website_add(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        category: str = "Allgemein",
        link_url: str | None = None,
        image_url: str | None = None,
        published: bool = True,
    ) -> None:
        if interaction.guild is None:
            await send_interaction_message(
                interaction,
                content="Dieser Befehl funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        db = await self.get_db_or_error(interaction)
        if db is None:
            return

        try:
            normalized_link_url = validate_optional_url(link_url)
            normalized_image_url = validate_optional_url(image_url)
        except ValueError as exc:
            await send_interaction_message(interaction, content=str(exc), ephemeral=True)
            return

        await self.ensure_settings_row(interaction.guild, interaction.user.id)

        entry = await db.fetchrow(
            """
            INSERT INTO discord.website_entries(
                guild_id,
                title,
                description,
                category,
                link_url,
                image_url,
                is_published,
                created_by
            )
            VALUES($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING entry_id, created_at
            """,
            interaction.guild.id,
            title.strip(),
            description.strip(),
            category.strip() or "Allgemein",
            normalized_link_url,
            normalized_image_url,
            published,
            interaction.user.id,
        )

        visibility = "sichtbar" if published else "versteckt"
        await send_interaction_message(
            interaction,
            content=f"Eintrag #{entry['entry_id']} wurde gespeichert und ist aktuell {visibility}.",
            ephemeral=True,
        )

    @app_commands.command(name="website_list", description="Zeigt die letzten Webseite-Eintraege")
    @app_commands.describe(limit="Wie viele Eintraege angezeigt werden sollen")
    async def website_list(self, interaction: discord.Interaction, limit: app_commands.Range[int, 1, LIST_LIMIT_MAX] = LIST_LIMIT_DEFAULT) -> None:
        if interaction.guild is None:
            await send_interaction_message(
                interaction,
                content="Dieser Befehl funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        db = await self.get_db_or_error(interaction)
        if db is None:
            return

        rows = await db.fetch(
            """
            SELECT entry_id, title, category, is_published, created_at
            FROM discord.website_entries
            WHERE guild_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            interaction.guild.id,
            limit,
        )
        if not rows:
            await send_interaction_message(
                interaction,
                content="Fuer diesen Server wurden noch keine Webseite-Eintraege gespeichert.",
                ephemeral=True,
            )
            return

        lines = []
        for row in rows:
            status = "online" if row["is_published"] else "draft"
            created_at = row["created_at"].strftime("%d.%m.%Y %H:%M")
            lines.append(
                f"#{row['entry_id']} | {row['title']} | {row['category']} | {status} | {created_at}"
            )

        embed = discord.Embed(
            title=f"Letzte {len(rows)} Webseite-Eintraege",
            description="\n".join(lines),
            colour=discord.Color.blurple(),
        )
        await send_interaction_message(interaction, embed=embed, ephemeral=True)

    @app_commands.command(name="website_publish", description="Schaltet einen Eintrag sichtbar oder unsichtbar")
    @app_commands.describe(entry_id="ID des Eintrags", published="True = sichtbar, False = versteckt")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def website_publish(self, interaction: discord.Interaction, entry_id: int, published: bool) -> None:
        if interaction.guild is None:
            await send_interaction_message(
                interaction,
                content="Dieser Befehl funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        db = await self.get_db_or_error(interaction)
        if db is None:
            return

        result = await db.execute(
            """
            UPDATE discord.website_entries
            SET is_published = $1,
                updated_at = NOW()
            WHERE guild_id = $2 AND entry_id = $3
            """,
            published,
            interaction.guild.id,
            entry_id,
        )
        if result.endswith("0"):
            await send_interaction_message(
                interaction,
                content=f"Eintrag #{entry_id} wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        status = "sichtbar" if published else "versteckt"
        await send_interaction_message(
            interaction,
            content=f"Eintrag #{entry_id} ist jetzt {status}.",
            ephemeral=True,
        )

    @app_commands.command(name="website_delete", description="Loescht einen Webseite-Eintrag")
    @app_commands.describe(entry_id="ID des Eintrags")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def website_delete(self, interaction: discord.Interaction, entry_id: int) -> None:
        if interaction.guild is None:
            await send_interaction_message(
                interaction,
                content="Dieser Befehl funktioniert nur auf einem Server.",
                ephemeral=True,
            )
            return

        db = await self.get_db_or_error(interaction)
        if db is None:
            return

        result = await db.execute(
            """
            DELETE FROM discord.website_entries
            WHERE guild_id = $1 AND entry_id = $2
            """,
            interaction.guild.id,
            entry_id,
        )
        if result.endswith("0"):
            await send_interaction_message(
                interaction,
                content=f"Eintrag #{entry_id} wurde nicht gefunden.",
                ephemeral=True,
            )
            return

        await send_interaction_message(
            interaction,
            content=f"Eintrag #{entry_id} wurde geloescht.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Website(bot))
