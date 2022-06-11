import discord
import os
import pytz
import dotenv

from discord import *
from discord.ext import commands
from datetime import *
from config.envirorment import *
from config.util import *

####################  function handling  ####################


dotenv.load_dotenv()


def load_extensions():
    for f in os.listdir("./cogs"):
        if f.endswith(".py") and not f.startswith("_"):
            bot.load_extension(f"cogs.{f[:-3]}")
            print(f"Geladen '{f}'")


async def send_all(msg: Message):
    servers = get_servers()
    content = msg.content
    author = msg.author
    attachments = msg.attachments
    de = pytz.timezone('Europe/Berlin')
    embed = discord.Embed(description=content, timestamp=datetime.now().astimezone(tz=de), color=author.color)

    icon = author.avatar_url
    embed.set_author(name=author.name, icon_url=icon)

    icon_url = "https://i.giphy.com/media/xT1XGzYCdltvOd9r4k/source.gif"
    icon = msg.guild.icon
    if icon:
        icon_url = icon
    embed.set_thumbnail(url=icon_url)
    embed.set_footer(text=f"Gesendet von Server '{msg.guild.name} : {msg.channel.name}'", icon_url=icon_url)

    links = f'[Stefans Server]({SERVER_INVITE}) ║ '
    globalchat = get_globalChat(msg.guild.id, msg.channel.id)

    if len(globalchat["invite"]) > 0:
        inv = globalchat["invite"]
        if 'discord.gg' not in inv:
            inv = 'https://discord.gg/{}'.format(inv)
        links += f'[Server Invite]({inv})'

    embed.add_field(name='⠀', value='⠀', inline=False)
    embed.add_field(name='Links & Hilfe', value=links, inline=False)

    if len(attachments) > 0:
        img = attachments[0]
        embed.set_image(url=img.url)

    for server in servers["servers"]:
        g: Guild = bot.get_guild(int(server["guildid"]))
        if g:
            c: TextChannel = g.get_channel(int(server["channelid"]))
            if c:
                perms: Permissions = c.permissions_for(g.get_member(bot.user.id))
                if perms.send_messages:
                    if perms.embed_links and perms.attach_files and perms.external_emojis:
                        await c.send(embed=embed)
                    else:
                        await c.send('{0}: {1}'.format(author.name, content))
                        await c.send('Es fehlen einige Berechtigungen. '
                                           '`Nachrichten senden` `Links einbetten` `Datein anhängen`'
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
            command_prefix=get_prefix,
            intents=discord.Intents.all()
        )

    async def on_ready(self):
        print(f"{self.user} is ready and online!")
        await self.change_presence(activity=Activity(type=ActivityType.watching, name=f"V2.1"))
        view = discord.ui.View(timeout=None)
        view.add_item(RoleButton())
        self.add_view(view)

    async def on_message(self, msg: Message):
        if msg.author.bot:
            return
        if not msg.content.startswith(await get_prefix(msg)):
            if get_globalChat(msg.guild.id, msg.channel.id):
                await send_all(msg)
        if bot.user.mentioned_in(msg) and len(msg.content):
            await msg.channel.send(f'Mein Prefix hier: `{await get_prefix(msg)}`', delete_after=15)
        await self.process_commands(msg)

    async def on_member_join(self, m: Member):
        g = self.get_guild(m.guild.id)
        if not m.bot:
            embed = Embed(title=f"Willkommen auf {g.name}, {m.name}",
                          description="Wir heißen dich herzlich Willkommen auf unserem Server! \n"
                                      "Bitte lies dir die Regeln durch um weiteren Zugriff zu erhalten",
                          colour=0x22a7f0)
            try:
                if not m.dm_channel:
                    await m.create_dm()
                await m.dm_channel.send(embed=embed)
            except discord.errors.Forbidden:
                print(f"Es konnte keine Willkommensnachricht an {m.mention} gesendet werden.")

            for c in m.guild.channels:
                if c.id == 615901690985447448:
                    embed = discord.Embed(title="Herzlich Willkommen",
                                          description=f"{m.mention}, Willkommen auf **{g.name}**",
                                          colour=0x22a7f0)
                    embed.set_thumbnail(url=g.icon)
                    await c.send(embed=embed, delete_after=30)
                    await draw_card_welcome(c, m)
        else:
            autoguild = AUTOROLE.get(g.id)
            if autoguild and autoguild["botrole"]:
                for roleId in autoguild["botrole"]:
                    r = g.get_role(roleId)
                    if r:
                        await m.add_roles(r)
                        c: TextChannel = discord.utils.get(m.guild.channels, id=615901690985447448)
                        await draw_card_welcome(c, m, True)

    async def on_guild_join(self, g: Guild):
        prefixes = read_json("prefix")
        prefixes[str(self.get_guild(g.id))] = "!"
        write_json(prefixes, "prefix")

    async def on_guild_remove(self, g: Guild):
        prefixes = read_json("prefix")
        prefixes.pop(str(self.get_guild(g.id)))
        write_json(prefixes, "prefix")


#############################################################


##################### Bot  initialising #####################


bot = Bot()


def main():
    print("lade Erweiterungen ...")
    load_extensions()
    print(f"-----")
    bot.run(os.getenv('TOKEN'))


#############################################################


if __name__ == "__main__":
    main()
