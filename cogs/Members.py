from discord import Member, Embed
from discord.ext import commands

from config.util import get_prefix, send_embed


class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.user_command(name="Userinfo",
                            description="Zeigt Info über ein Mitglied")
    async def _userinfo(self, ctx, member: Member = None):
        if member:
            embed = Embed(title=f"Userinfo für {member.name}",
                          description=f"Dies ist eine Userinfo für den User {member.mention}",
                          color=0x22a7f0)
            embed.add_field(name="Server beigetreten", value=member.joined_at.strftime("%d/%m/%Y, %H:%M:%S"),
                            inline=True)
            embed.add_field(name="Discord beigetreten", value=member.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                            inline=True)
            rollen = ""
            for role in member.roles:
                if not role.is_default():
                    rollen += f"{role.mention} \r\n"
            if rollen:
                embed.add_field(name="Rollen", value=rollen, inline=False)
            embed.set_thumbnail(url=member.avatar)
            embed.set_footer(text=f"*LEL* for more info")
        else:
            embed = Embed(title=f"Userinfo für {ctx.author.name}",
                          description=f"Dies ist eine Userinfo für den User {ctx.author.mention}",
                          color=0x22a7f0)
            embed.add_field(name="Server beigetreten", value=ctx.author.joined_at.strftime("%d/%m/%Y, %H:%M:%S"),
                            inline=True)
            embed.add_field(name="Discord beigetreten", value=ctx.author.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
                            inline=True)
            rollen = ""
            for role in ctx.author.roles:
                if not role.is_default():
                    rollen += f"{role.mention} \r\n"
            if rollen:
                embed.add_field(name="Rollen", value=rollen, inline=False)
            embed.set_thumbnail(url=ctx.author.avatar)
            embed.set_footer(text=f"*LEL* for more info")

        await send_embed(ctx, embed, 15)
        await ctx.respond('T')


def setup(bot):
    bot.add_cog(Members(bot))
