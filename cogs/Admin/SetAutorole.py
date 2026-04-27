import discord
from discord import app_commands
from discord.ext import commands

from config.Util import handle_app_command_error, send_interaction_message


class SetAutorole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setautorole", description="Rollen in der DB hinterlegen")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(memberrole="Rolle fuer Member", botrole="Rolle fuer Bots")
    async def setautorole(
        self,
        interaction: discord.Interaction,
        memberrole: discord.Role,
        botrole: discord.Role,
    ) -> None:
        if interaction.guild is None:
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return
        if self.bot.db is None:
            await send_interaction_message(interaction, content="Die Datenbank ist aktuell nicht verfuegbar.", ephemeral=True)
            return

        await self.bot.db.execute(
            "INSERT INTO autorole(guild_id, memberrole_id, botrole_id) VALUES($1, $2, $3)",
            interaction.guild.id,
            memberrole.id,
            botrole.id,
        )
        await send_interaction_message(interaction, content="Autorole hinzugefuegt.", ephemeral=True)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetAutorole(bot))
