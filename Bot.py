import asyncio

import discord
import dotenv

from discord import Message, ActivityType, Activity, Member, TextChannel, Embed, Forbidden
from discord.ext import commands, tasks

from config.Environment import load_env, VERSION
from config.Util import RoleButton, draw_card_welcome, set_prefix, \
    get_prefix, get_autorole, is_globalchat, send_all, load_extensions, create_db_pool

dotenv.load_dotenv()


########################### Klasse ##########################
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            debug_guilds=[615901690536787983],
            owner_id=183185835477172226,
            command_prefix=set_prefix,
            intents=discord.Intents.all()
        )
        self.stats_channel.start()

    def cog_unload(self):
        pass
        self.stats_channel.stop()

    async def on_ready(self):
        print(f"{self.user} is ready and online!")
        await self.change_presence(activity=Activity(type=ActivityType.watching, name=f'{VERSION} by PeeT_Tea#2408'))
        view = discord.ui.View(timeout=None)
        view.add_item(RoleButton(self))
        self.add_view(view)

    async def on_message(self, message: Message):
        if message.author.bot:
            return
        if not message.content.startswith(await get_prefix(self, message)):
            if await is_globalchat(self, message.guild.id, message.channel.id):
                await send_all(self, message)
        if bot.user.mentioned_in(message) and len(message.content):
            await message.channel.send(f'Mein Prefix hier: `{await get_prefix(self, message)}`', delete_after=15)
        await self.process_commands(message)

    async def on_member_join(self, member: Member):
        g = self.get_guild(member.guild.id)
        if not member.bot:
            embed = Embed(title=f"Willkommen auf {g.name}, {member.name}",
                          description="Wir heißen dich herzlich Willkommen auf unserem Server! \n"
                                      "Bitte lies dir die Regeln durch um weiteren Zugriff zu erhalten",
                          colour=0x22a7f0)
            try:
                if not member.dm_channel:
                    await member.create_dm()
                await member.dm_channel.send(embed=embed)
            except Forbidden:
                print(f"Es konnte keine Willkommensnachricht an {member.mention} gesendet werden.")

            for c in g.channels:
                if c.id == 615901690985447448:
                    embed = discord.Embed(title="Herzlich Willkommen",
                                          description=f"{member.mention}, Willkommen auf **{g.name}**",
                                          colour=0x22a7f0)
                    embed.set_thumbnail(url=g.icon)
                    await c.send(embed=embed, delete_after=30)
                    await draw_card_welcome(c, member)
        else:
            r = g.get_role(await get_autorole(self, member, g))
            if r:
                await member.add_roles(r)
                c: TextChannel = discord.utils.get(member.guild.channels, id=615901690985447448)
                await draw_card_welcome(c, member, True)

    # stats channel #
    @tasks.loop(seconds=150)
    async def stats_channel(self):
        guild = self.get_guild(615901690536787983)
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
        await self.wait_until_ready()


##################### Bot  initialising #####################
bot = Bot()
bot.remove_command('help')


def main():
    print("lade Erweiterungen ...")
    load_extensions(bot)
    print(f"-----")
    bot.loop.run_until_complete(create_db_pool(bot))
    bot.run(load_env('TOKEN', 'unknown'))


#############################################################
if __name__ == "__main__":
    main()
