from discord import option, Role
from discord.ext import commands


class SetAutorole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='setautorole', description='Rollen in der DB hinterlegen')
    @commands.has_permissions(administrator=True)
    @option('memberrole', desription='choose memberrole')
    @option('botrole', description='choose botrole')
    async def setautorole(self, ctx, memberrole: Role, botrole: Role):
        await self.bot.db.execute(f'INSERT INTO autorole(guild_id, memberrole_id, botrole_id) '
                                  f'VALUES($1, $2, $3)', ctx.guild.id, memberrole.id, botrole.id)
        await ctx.send('Autorole hinzugefügt')

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("You need administrator permissions!", delete_after=1, ephemeral=True)
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored


def setup(bot):
    bot.add_cog(SetAutorole(bot))
