import os

import discord
from discord.ext import commands
from Bot import StandardButton


class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(description='test')
    async def test(self, ctx):
        modules = []
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                modules.append(file[:-3])
        print(modules)

    @commands.command()
    async def hallo(self, ctx):
        view = discord.ui.View(timeout=None)
        view.add_item(StandardButton())
        await ctx.send(f"Penis {ctx.author.mention}!", view=view)


def setup(bot):
    bot.add_cog(Test(bot))
