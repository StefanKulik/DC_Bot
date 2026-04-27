import discord
from discord import app_commands
from discord.ext import commands

from config.Environment import SERVER_INVITE
from config.Util import handle_app_command_error, send_interaction_message


class Kick(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Member vom Server kicken")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Mitglied", reason="Grund fuer den Kick")
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return

        kick_reason = reason or "LOL"
        await member.kick(reason=kick_reason)

        embed = discord.Embed(title=f"Member {member.name} gekickt! Grund: {kick_reason}")
        await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)

        if member.bot:
            return

        dm_embed = discord.Embed(title=f"Du wurdest von {interaction.guild.name} gekickt!")
        dm_embed.add_field(name="Grund", value=kick_reason, inline=False)
        try:
            if member.dm_channel is None:
                await member.create_dm()
            await member.dm_channel.send(embed=dm_embed)
            await member.dm_channel.send(SERVER_INVITE)
        except discord.Forbidden:
            print(f"Es konnte keine Nachricht an {member.mention} gesendet werden.")

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Kick(bot))
