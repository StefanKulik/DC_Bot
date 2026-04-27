import discord
from discord import app_commands
from discord.ext import commands

from config.Util import handle_app_command_error, is_not_pinned, send_interaction_message


PROTECTED_CHANNEL_ID = 615901690985447448


class Clear(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clear", description="Nachrichten im Channel loeschen")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(num="Anzahl der zu loeschenden Nachrichten")
    async def clear(self, interaction: discord.Interaction, num: app_commands.Range[int, 1, 100] = 10) -> None:
        channel = interaction.channel
        if interaction.guild is None or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur in Textkanaelen.", ephemeral=True)
            return

        if channel.id == PROTECTED_CHANNEL_ID:
            embed = discord.Embed(description="Dieser Channel darf nicht geleert werden!")
            await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)
            return

        deleted_messages = await channel.purge(limit=int(num), check=is_not_pinned)
        embed = discord.Embed(description=f"**{len(deleted_messages)}** Nachrichten geloescht.")
        await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Clear(bot))
