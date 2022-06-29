import discord
from discord.ext import commands
from discord.ui import View

from config.Util import StandardButton, RoleButton


########################### Klasse ##########################
class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(description='test')
    @commands.has_permissions(administrator=True)
    async def test(self, ctx):
        view = discord.ui.View(timeout=None)
        view.add_item(StandardButton())
        await ctx.send(view=view)

    @commands.slash_command()
    @commands.has_permissions(administrator=True)
    async def rules(self, ctx):
        await ctx.channel.purge(limit=1)
        emb = discord.Embed(title=f"Regeln auf {ctx.guild.name}",
                            description=f"Serverbesitzer: {ctx.guild.owner.mention}")
        emb.set_thumbnail(url=ctx.guild.icon)
        emb.add_field(name="Regel 1", value="Have Fun", inline=False)
        emb.add_field(name="Regel 2", value="Keine Beleidigungen", inline=False)
        emb.add_field(name="Regel 3", value="Respektvoll sein", inline=False)
        emb.add_field(name="Regel 4", value="Regel 1", inline=False)
        emb.add_field(name="\u200b \n\n",
                      value=f"Klicke auf 'Verifizieren' um die Regeln zu akzeptieren und weiteren Zugriff auf den Server zu erhalten")
        view = View(timeout=None)
        view.add_item(RoleButton(self.bot))
        await ctx.send(embed=emb, view=view)

    @commands.command()
    async def hallo(self, ctx):
        view = discord.ui.View(timeout=None)
        view.add_item(StandardButton())
        await ctx.send(f"Hallo {ctx.author.mention}!", view=view)


#############################################################
def setup(bot):
    bot.add_cog(Test(bot))
