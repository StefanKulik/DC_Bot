import os

from discord import option, Member, Embed, Forbidden
from discord.ext import commands


class Kick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="kick", description="Member vom Server kicken")
    @commands.has_permissions(administrator=True)
    @option('member', description='auswählen wer gekickt werden soll')
    async def kick(self, ctx, member: Member, reason=None):
        if reason is None:
            reason = "LOL"
        if member:
            await member.kick(reason=reason)
            await ctx.send(embed=Embed(title=f"Member {member.name} gekickt! Grund: {reason}"),
                           delete_after=5)
            if not member.bot:
                embed = Embed(title=f"Du wurdest von {ctx.guild.name} gekickt!")
                embed.add_field(name="Grund:", value=f" {reason}")
                try:
                    if not member.dm_channel:
                        await member.create_dm()
                    await member.dm_channel.send(embed=embed)
                    await member.dm_channel.send(os.getenv("SERVER_INVITE"))
                except Forbidden:
                    print(f"Es konnte keine Nachricht an {member.mention} gesendet werden.")

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("You need administrator permissions!", delete_after=1, ephemeral=True)
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored


def setup(bot):
    bot.add_cog(Kick(bot))
