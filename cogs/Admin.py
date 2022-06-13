import asyncio
import os

import discord
from discord import option, Embed, ExtensionAlreadyLoaded, ExtensionNotLoaded, Member, Role
from discord.ext import commands, tasks

from config.util import is_not_pinned, read_json, write_json

# TODO: Kick, Ban, Tempban, Unban, Banlist, Mute, Unmute,


modules = []
for file in os.listdir("./cogs"):
    if file.endswith(".py") and not file.startswith("_"):
        modules.append(file[:-3])


async def load(self, ctx, module: str):
    if module is None:
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py") and not cog.startswith("_"):
                try:
                    self.bot.load_extension(f"cogs.{cog[:-3]}")
                except Exception as e:
                    if isinstance(e, ExtensionAlreadyLoaded):
                        await ctx.respond(f'{cog[:-3]} already loaded')
                    else:
                        await ctx.respond(f'{format(type(e).__name__)}: {e}')
                else:
                    await ctx.respond('\N{OK HAND SIGN}')
    else:
        try:
            self.bot.load_extension(f'cogs.{module}')
        except Exception as e:
            await ctx.respond(f'{format(type(e).__name__)}: {e}')
        else:
            await ctx.respond('\N{OK HAND SIGN}')


async def unload(self, ctx, module: str):
    if module is None:
        e = Embed(title='Alle Module wurden entladen...')
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py") and not cog.startswith("_"):
                try:
                    self.bot.unload_extension(f"cogs.{cog[:-3]}")
                except Exception as e:
                    if isinstance(e, ExtensionNotLoaded):
                        await ctx.respond(f'{cog[:-3]} was not loaded')
                    else:
                        await ctx.respond(f'{format(type(e).__name__)}: {e}')
        await ctx.respond(embed=e)
    else:
        try:
            self.bot.unload_extension(f'cogs.{module}')
        except Exception as e:
            await ctx.respond(f'{format(type(e).__name__)}: {e}')
        else:
            await ctx.respond('\N{OK HAND SIGN}')


async def reload(self, ctx, module: str):
    if module is None:
        e = Embed(title='Alle Module werden neugeladen...')
        for cog in os.listdir("./cogs"):
            if cog.endswith(".py") and not cog.startswith("_"):
                try:
                    self.bot.reload_extension(f"cogs.{cog[:-3]}")
                except Exception as e:
                    await ctx.respond(f'{format(type(e).__name__)}: {e}')
                else:
                    e.add_field(name=f'{cog[:-3]}', value='\N{OK HAND SIGN}', inline=True)
        await ctx.respond(embed=e)
    else:
        try:
            self.bot.reload_extension(f'cogs.{module}')
        except Exception as e:
            await ctx.respond(f'{format(type(e).__name__)}: {e}')
        else:
            await ctx.respond('\N{OK HAND SIGN}')


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

    @commands.slash_command(name='cog', description='Cog load, unload, reload')
    @option('function', description='choose Function', choices=['load', 'unload', 'reload'])
    @option('module', description='choose Module', choices=modules)
    @commands.has_permissions(administrator=True)
    async def _cog(self, ctx, function: str, module: str = None):
        if function == 'load':
            await load(self, ctx, module)
        if function == 'unload':
            await unload(self, ctx, module)
        if function == 'reload':
            await reload(self, ctx, module)

    @commands.slash_command(name='clear')
    @option('num', description='Enter a number', min_value=1, max_value=100, default=10)
    @commands.has_permissions(administrator=True)
    async def _clear(self, ctx, num: int):
        if ctx.channel.id == 615901690985447448:
            await ctx.send(embed=discord.Embed(description="Dieser Channel darf nicht geleert werden!"),
                           delete_after=5)
        await ctx.channel.purge(limit=int(num) + 1, check=is_not_pinned)
        await ctx.channel.send(embed=discord.Embed(description=f"**{int(num)}** Nachrichten gelöscht."),
                               delete_after=5)

    @commands.slash_command(name='changeprefix', description='Prefix ändern')
    @option('prefix', description='pick Prefix', choices=['!', '<', '>', '-', '.', '?', '$', '#'])
    @commands.has_permissions(administrator=True)
    async def _changeprefix(self, ctx, prefix: str):
        await ctx.channel.purge(limit=1)
        # prefixes = read_json("prefix")
        # prefixes[str(ctx.guild.id)] = prefix
        # write_json(prefixes, "prefix")
        await self.bot.db.execute('UPDATE guilds SET prefix = $1 WHERE guild_id = $2', prefix, ctx.guild.id)
        await ctx.respond(embed=discord.Embed(title=f"Prefix geändert zu '{prefix}'",
                                              description="Schreibe /changeprefix <prefix> zum erneuten ändern."),
                          delete_after=5,
                          ephemeral=True)

    @commands.slash_command(name='setautorole')
    @option('memberrole', desription='choose memberrole')
    @option('botrole', description='choose botrole')
    @commands.has_permissions(administrator=True)
    async def _setautorole(self, ctx, memberrole: Role, botrole: Role):
        await self.bot.db.execute(f'INSERT INTO autorole(guild_id, memberrole_id, botrole_id) '
                                  f'VALUES($1, $2, $3)', ctx.guild.id, memberrole.id, botrole.id)
        await ctx.send('Autorole hinzugefügt')

    @commands.slash_command(name="kick",
                            description="Member vom Server kicken")
    @option('member', description='auswählen wer gekickt werden soll')
    @commands.has_permissions(administrator=True)
    async def _kick(self, ctx, member: Member, reason=None):
        if reason is None:
            reason = "LOL"
        if member:
            await member.kick(reason=reason)
            await ctx.send(embed=discord.Embed(title=f"Member {member.name} gekickt! Grund: {reason}"),
                           delete_after=5)
            if not member.bot:
                embed = discord.Embed(title=f"Du wurdest von {ctx.guild.name} gekickt!")
                embed.add_field(name="Grund:", value=f" {reason}")
                try:
                    if not member.dm_channel:
                        await member.create_dm()
                    await member.dm_channel.send(embed=embed)
                    await member.dm_channel.send(os.getenv("SERVER_INVITE"))
                except discord.errors.Forbidden:
                    print(f"Es konnte keine Nachricht an {member.mention} gesendet werden.")

    @commands.Cog.listener()
    async def on_application_command_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("Sorry, you can only use this with administrator permissions!", delete_after=1, ephemeral=True)
        else:
            raise error  # Here we raise other errors to ensure they aren't ignored


def setup(bot):
    bot.add_cog(Admin(bot))
