import asyncio
import os

import discord
from discord import SlashCommandGroup, Member
from discord.ext import commands, tasks

from config.util import is_not_pinned, get_path


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
    async def load(self, ctx, module: str):
        try:
            self.bot.load_extension(f'cogs.{module}')
        except Exception as e:
            await ctx.respond('\N{PISTOL}')
            await ctx.respond('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.respond('\N{OK HAND SIGN}')

    @handlerCog.command()
    async def unload(self, ctx, module: str):
        try:
            self.bot.unload_extension(f'cogs.{module}')
        except Exception as e:
            await ctx.respond('\N{PISTOL}')
            await ctx.respond('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.respond('\N{OK HAND SIGN}')

    @handlerCog.command()
    async def reload(self, ctx, module: str):
        try:
            self.bot.unload_extension(f'cogs.{module}')
            self.bot.load_extension(f'cogs.{module}')
        except Exception as e:
            await ctx.respond('\N{PISTOL}')
            await ctx.respond('{}: {}'.format(type(e).__name__, e))
        else:
            await ctx.respond('\N{OK HAND SIGN}')

    @commands.command()
    async def thread(self, ctx, member: Member):
        # pass
        message = await ctx.send("lol")
        await message.create_thread(name=member.name, auto_archive_duration=60)

    @commands.slash_command(name='clear')
    async def clear(self, ctx, num: int):
        if int(num) > 100 or int(num) < 1:
            await ctx.channel.purge(limit=1, check=is_not_pinned)
            await ctx.send(
                embed=discord.Embed(description="Bitte nur zwischen 1 und 100 Nachrichten löschen!"),
                delete_after=5)
            return
        if ctx.channel.id == 615901690985447448:
            await ctx.send(embed=discord.Embed(description="Dieser Channel darf nicht geleert werden!"),
                           delete_after=5)
            return
        await ctx.channel.purge(limit=int(num) + 1, check=is_not_pinned)
        await ctx.channel.send(embed=discord.Embed(description=f"**{int(num)}** Nachrichten gelöscht."),
                               delete_after=5)


def setup(bot):
    bot.add_cog(Admin(bot))
