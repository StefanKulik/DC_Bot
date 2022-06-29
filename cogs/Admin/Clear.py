from discord import option, Embed
from discord.ext import commands

from config.Util import is_not_pinned


class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='clear', description='Clear Channel')
    @commands.has_permissions(administrator=True)
    @option('num', description='Enter a number', min_value=1, max_value=100, default=10)
    async def clear(self, ctx, num: int):
        if ctx.channel.id == 615901690985447448:
            await ctx.send(embed=Embed(description="Dieser Channel darf nicht geleert werden!"),
                           delete_after=5)
        await ctx.channel.purge(limit=int(num) + 1, check=is_not_pinned)
        await ctx.channel.send(embed=Embed(description=f"**{int(num)}** Nachrichten gelöscht."),
                               delete_after=5)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("You need administrator permissions!", delete_after=1, ephemeral=True)
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored


def setup(bot):
    bot.add_cog(Clear(bot))
