from discord import option
from discord.ext import commands

from config.Environment import COG_HANDLER
from config.Util import get_modules, load, unload, reload


class CogHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='cog', description='Cog load, unload, reload')
    @commands.has_permissions(administrator=True)
    @option('function', description='choose Function', choices=COG_HANDLER)
    @option('module', description='choose Module', choices=get_modules())
    async def handler(self, ctx, function: str, module: str = None):
        if function == 'load':
            await load(self, ctx, module)
        if function == 'unload':
            await unload(self, ctx, module)
        if function == 'reload':
            await reload(self, ctx, module)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("You need administrator permissions!", delete_after=1, ephemeral=True)
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored


def setup(bot):
    bot.add_cog(CogHandler(bot))
