import discord
from discord.ext import commands
from Bot import StandardButton


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description='test')
    async def test(self, ctx):
        await ctx.respond('Test', ephemeral=True)

    @commands.command()
    async def hallo(self, ctx):
        view = discord.ui.View(timeout=None)
        view.add_item(StandardButton())
        await ctx.send(f"Penis {ctx.author.mention}!", view=view)


def setup(bot):
    bot.add_cog(Test(bot))
