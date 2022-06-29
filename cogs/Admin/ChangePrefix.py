from discord import option, Embed
from discord.ext import commands

from config.Environment import PREFIX_LIST


class Prefix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='changeprefix', description='Prefix ändern')
    @commands.has_permissions(administrator=True)
    @option('prefix', description='pick Prefix', choices=PREFIX_LIST)
    async def changeprefix(self, ctx, prefix: str):
        await ctx.channel.purge(limit=1)
        await self.bot.db.execute('UPDATE guilds SET prefix = $1 WHERE guild_id = $2', prefix, ctx.guild.id)
        await ctx.respond(embed=Embed(title=f"Prefix geändert zu '{prefix}'",
                                      description="Schreibe /changeprefix <prefix> zum erneuten ändern."),
                          delete_after=5,
                          ephemeral=True)

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("You need administrator permissions!", delete_after=1, ephemeral=True)
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored


def setup(bot):
    bot.add_cog(Prefix(bot))
