import discord
import os
import pytz
import dotenv
import asyncpg

from discord import Message, ActivityType, Activity, Guild, Permissions, Member, TextChannel, Embed, Forbidden
from discord.ext import commands
from datetime import *
from config.envirorment import SERVER_INVITE, DATABASE_URL, load_env
from config.util import RoleButton, draw_card_welcome, set_prefix, \
    get_prefix, get_autorole, get_servers, get_globalchat, is_globalchat

####################  function handling  ####################


dotenv.load_dotenv()


def load_extensions():
    for f in os.listdir("./cogs"):
        if f.endswith(".py") and not f.startswith("_"):
            bot.load_extension(f"cogs.{f[:-3]}")
            print(f"Geladen '{f}'")


async def create_db_pool():
    print('Connect to database...')
    bot.db = await asyncpg.create_pool(dsn=DATABASE_URL)
    print('Connection successful')


async def send_all(bot, msg: Message):
    servers = []
    for server in await get_servers(bot):
        servers.append(server['guild_id'])

    content = msg.content
    author = msg.author
    attachments = msg.attachments
    de = pytz.timezone('Europe/Berlin')
    embed = discord.Embed(description=content, timestamp=datetime.now().astimezone(tz=de), color=author.color)

    icon = author.avatar
    embed.set_author(name=author.name, icon_url=icon)

    icon_url = "https://i.giphy.com/media/xT1XGzYCdltvOd9r4k/source.gif"
    icon = msg.guild.icon
    if icon:
        icon_url = icon
    embed.set_thumbnail(url=icon_url)
    embed.set_footer(text=f"Gesendet von Server '{msg.guild.name} : {msg.channel.name}'", icon_url=icon_url)

    links = f'[Stefans Server]({SERVER_INVITE}) ║ '
    globalchat = await get_globalchat(bot, msg.guild.id)

    if len(globalchat[0]['invite']) > 0:
        inv = globalchat[0]['invite']
        if 'discord.gg' not in inv:
            inv = 'https://discord.gg/{}'.format(inv)
        links += f'[Server Invite]({inv})'

    embed.add_field(name='⠀', value='⠀', inline=False)
    embed.add_field(name='Links & Hilfe', value=links, inline=False)

    if len(attachments) > 0:
        img = attachments[0]
        embed.set_image(url=img.url)

    for server in servers:
        gc = await get_globalchat(bot, server)
        g: Guild = bot.get_guild(gc[0]['guild_id'])
        if g:
            c: TextChannel = g.get_channel(gc[0]['channel_id'])
            if c:
                permissions: Permissions = c.permissions_for(g.get_member(bot.user.id))
                if permissions.send_messages:
                    if permissions.embed_links and permissions.attach_files and permissions.external_emojis:
                        await c.send(embed=embed)
                    else:
                        await c.send('{0}: {1}'.format(author.name, content))
                        await c.send('Es fehlen einige Berechtigungen. '
                                           '`Nachrichten senden` `Links einbetten` `Dateien anhängen`'
                                           '`Externe Emojis verwenden`')
    await msg.delete()


#############################################################

class Bot(commands.Bot):
    async def sync_commands(self) -> None:
        pass

    def __init__(self):
        super().__init__(
            debug_guilds=[615901690536787983],
            owner_id=183185835477172226,
            command_prefix=set_prefix,
            intents=discord.Intents.all()
        )

    async def on_ready(self):
        print(f"{self.user} is ready and online!")
        await self.change_presence(activity=Activity(type=ActivityType.watching, name=f"V2.2"))
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

#############################################################


##################### Bot  initialising #####################

bot = Bot()


def main():
    print("lade Erweiterungen ...")
    load_extensions()
    print(f"-----")
    bot.loop.run_until_complete(create_db_pool())
    bot.run(load_env('TOKEN', 'unknown'))

#############################################################


if __name__ == "__main__":
    main()
