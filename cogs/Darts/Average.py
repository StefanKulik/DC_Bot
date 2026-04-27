import discord
from discord import app_commands
from discord.ext import commands


class Average(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="average", description="Average Darts")
    @app_commands.guild_only()
    @app_commands.describe(points="Geworfene Punkte", darts="Geworfene Darts")
    async def average(
        self,
        interaction: discord.Interaction,
        points: int,
        darts: app_commands.Range[int, 1],
    ) -> None:
        average = points / (darts / 3)
        embed = discord.Embed(
            title=f"Average: {average:.2f}",
            description=f"Points **{points}** / Darts **{darts}**",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Average(bot))
