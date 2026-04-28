import discord
from discord import app_commands
from discord.ext import commands

from config.Environment import PREFIX_LIST
from config.Util import handle_app_command_error, send_interaction_message


PREFIX_CHOICES = [app_commands.Choice(name=prefix, value=prefix) for prefix in PREFIX_LIST]


class Prefix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="changeprefix", description="Prefix aendern")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(prefix="Neuer Prefix")
    @app_commands.choices(prefix=PREFIX_CHOICES)
    async def changeprefix(self, interaction: discord.Interaction, prefix: str) -> None:
        if interaction.guild is None:
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return
        if self.bot.db is None:
            await send_interaction_message(interaction, content="Die Datenbank ist aktuell nicht verfuegbar.", ephemeral=True)
            return

        await self.bot.db.set_prefix(interaction.guild.id, prefix)
        embed = discord.Embed(
            title=f"Prefix geaendert zu '{prefix}'",
            description="Schreibe /changeprefix <prefix> zum erneuten Aendern.",
        )
        await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Prefix(bot))
