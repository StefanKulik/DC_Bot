from discord import Member, Embed, Color
from discord.ext import commands

from config.util import send_embed, get_prefix, get_prefix_context


########################### Klasse ##########################
class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.user_command(name='Memberliste', desciption='Listet alle Member auf')
    async def memberlist(self, ctx, member):
        member_list = ctx.guild.members
        member_count = sum(not member.bot for member in member_list)
        liste = ""
        for member in member_list:
            if not member.bot:
                liste += f"{member.mention}\r\n"
        embed = Embed(title=f"Member Liste (Anzahl: {member_count})", description=liste)
        embed.set_footer(text=f"*{await get_prefix_context(self.bot, ctx)}help* for more info")
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.user_command(name='Botiste', description='Listet alle Bots auf')
    async def botliste(self, ctx, member):
        bot_list = ctx.guild.members
        _bot_count = sum(bot.bot for bot in bot_list)
        liste = ""
        for _bot in bot_list:
            if _bot.bot:
                liste += f"{_bot.mention}\r\n"
        embed = Embed(title=f"Bot Liste (Anzahl: {_bot_count})", description=liste)
        embed.set_footer(text=f"*{await get_prefix_context(self.bot, ctx)}help* for more info")
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.user_command(name="Userinfo", description="Zeigt Info über ein Mitglied")
    async def userinfo(self, ctx, member):
        # if member:
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
        url = member.avatar
        if url:
            embed.set_thumbnail(url=url)
        embed.set_footer(text=f"*LEL* for more info")
        # else:
        #     embed = Embed(title=f"Userinfo für {ctx.author.name}",
        #                   description=f"Dies ist eine Userinfo für den User {ctx.author.mention}",
        #                   color=0x22a7f0)
        #     embed.add_field(name="Server beigetreten", value=ctx.author.joined_at.strftime("%d/%m/%Y, %H:%M:%S"),
        #                     inline=True)
        #     embed.add_field(name="Discord beigetreten", value=ctx.author.created_at.strftime("%d/%m/%Y, %H:%M:%S"),
        #                     inline=True)
        #     rollen = ""
        #     for role in ctx.author.roles:
        #         if not role.is_default():
        #             rollen += f"{role.mention} \r\n"
        #     if rollen:
        #         embed.add_field(name="Rollen", value=rollen, inline=False)
        #     embed.set_thumbnail(url=ctx.author.avatar)
        #     embed.set_footer(text=f"*LEL* for more info")

        await ctx.respond(embed=embed, ephemeral=True)

    @commands.user_command(name='Serverinfo')
    async def serverinfo(self, ctx, member):
        member = member
        name = ctx.guild.name
        description = ctx.guild.description
        region = ctx.guild.region
        icon = ctx.guild.icon
        member_count = ctx.guild.member_count
        owner = ctx.guild.owner

        server = Embed(
            title=f"*{name}* \u200b Informationen",
            description=description,
            color=Color.dark_blue()
        )
        server.set_thumbnail(url=icon)
        server.add_field(name="Region", value=region, inline=True)
        server.add_field(name="Besitzer", value=owner, inline=True)
        server.add_field(name="Anzahl Mitglieder", value=member_count, inline=False)
        await ctx.respond(embed=server, ephemeral=True)


#############################################################
def setup(bot):
    bot.add_cog(Members(bot))
