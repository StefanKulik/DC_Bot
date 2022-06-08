import asyncio

import discord
from discord import SlashCommandGroup, Member
from discord.ext import commands, tasks


class Admin(commands.Cog, description='Admin Befehle'):
    def __init__(self, bot):
        self.bot = bot
        self.stats_channel.start()

    def cog_unload(self):
        self.stats_channel.stop()

    # stats channel #
    @tasks.loop(seconds=150)
    async def stats_channel(self):
        guild = self.bot.get_guild(615901690536787983)
        channel_online = discord.utils.get(guild.channels, id=877700163295125524)
        channel_total = discord.utils.get(guild.channels, id=877689459804622869)
        channel_human = discord.utils.get(guild.channels, id=877693165325385769)
        channel_bot = discord.utils.get(guild.channels, id=877698704444899349)
        await channel_online.edit(
            name=f'Online: {sum(member.status != discord.Status.offline for member in guild.members)}')
        await channel_total.edit(name=f'Gesamt Mitglieder: {guild.member_count}')
        await channel_human.edit(name=f'Menschen: {sum(not member.bot for member in guild.members)}')
        await channel_bot.edit(name=f'Bots: {sum(member.bot for member in guild.members)}')

    @stats_channel.before_loop
    async def before_member_channel(self):
        await self.bot.wait_until_ready()

    handlerCog = SlashCommandGroup('cog', 'Cog Handling -> laden / entladen / neuladen')

    @handlerCog.command()
    async def load(self, ctx):
        pass

    @handlerCog.command()
    async def unload(self, ctx):
        pass

    @handlerCog.command()
    async def reload(self, ctx):
        pass

    @commands.command()
    async def thread(self, ctx, member: Member):
        # pass
        message = await ctx.send("lol")
        await message.create_thread(name=member.name, auto_archive_duration=60)


def setup(bot):
    bot.add_cog(Admin(bot))
