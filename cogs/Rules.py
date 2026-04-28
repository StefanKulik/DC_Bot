import discord
from discord import app_commands
from discord.ext import commands

from config.Util import RoleButton, StandardButton, handle_app_command_error


class Rules(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rules", description="Regelwerk senden")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def rules(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message("Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        embed = discord.Embed(
            title=f"Regeln auf {interaction.guild.name}",
            description=f"Serverbesitzer: {interaction.guild.owner.mention}",
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.add_field(name="Regel 1", value="Have Fun", inline=False)
        embed.add_field(name="Regel 2", value="Keine Beleidigungen", inline=False)
        embed.add_field(name="Regel 3", value="Respektvoll sein", inline=False)
        embed.add_field(name="Regel 4", value="Regel 1", inline=False)
        embed.add_field(
            name="\u200b \n\n",
            value="Klicke auf 'Verifizieren', um die Regeln zu akzeptieren und weiteren Zugriff auf den Server zu erhalten.",
        )
        view = discord.ui.View(timeout=None)
        view.add_item(RoleButton(self.bot))
        await interaction.channel.send(embed=embed, view=view)
        await interaction.followup.send("Regeln wurden gesendet.", ephemeral=True)


    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Rules(bot))
