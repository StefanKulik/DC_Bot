import discord
import os
import pytz
import dotenv

from discord import Message, Guild, TextChannel, Permissions, Embed
from discord.ext import commands
from datetime import datetime

from config.envirorment import SERVER_INVITE, AUTOROLE
from config.util import get_prefix, get_globalChat, get_servers, draw_card_welcome, read_json, write_json


###################  function handling  ####################

dotenv.load_dotenv()


def load_extensions():
    for file in os.listdir("./cogs"):
        if file.endswith(".py") and not file.startswith("_"):
            bot.load_extension(f"cogs.{file[:-3]}")
            print(f"Geladen '{file}'")


async def sendAll(msg: Message):
    servers = get_servers()
    content = msg.content
    author = msg.author
    attachments = msg.attachments
    de = pytz.timezone('Europe/Berlin')
    embed = discord.Embed(description=content, timestamp=datetime.now().astimezone(tz=de), color=author.color)

    icon = author.avatar_url
    embed.set_author(name=author.name, icon_url=icon)

    icon_url = "https://i.giphy.com/media/xT1XGzYCdltvOd9r4k/source.gif"
    icon = msg.guild.icon_url
    if icon:
        icon_url = icon
    embed.set_thumbnail(url=icon_url)
    embed.set_footer(text=f"Gesendet von Server '{msg.guild.name} : {msg.channel.name}'", icon_url=icon_url)

    links = f'[Stefans Server]({SERVER_INVITE}) ║ '
    globalchat = get_globalChat(msg.guild.id, msg.channel.id)

    if len(globalchat["invite"]) > 0:
        invite = globalchat["invite"]
        if 'discord.gg' not in invite:
            invite = 'https://discord.gg/{}'.format(invite)
        links += f'[Server Invite]({invite})'

    embed.add_field(name='⠀', value='⠀', inline=False)
    embed.add_field(name='Links & Hilfe', value=links, inline=False)

    if len(attachments) > 0:
        img = attachments[0]
        embed.set_image(url=img.url)

    for server in servers["servers"]:
        guild: Guild = bot.get_guild(int(server["guildid"]))
        if guild:
            channel: TextChannel = guild.get_channel(int(server["channelid"]))
            if channel:
                perms: Permissions = channel.permissions_for(guild.get_member(bot.user.id))
                if perms.send_messages:
                    if perms.embed_links and perms.attach_files and perms.external_emojis:
                        await channel.send(embed=embed)
                    else:
                        await channel.send('{0}: {1}'.format(author.name, content))
                        await channel.send('Es fehlen einige Berechtigungen. '
                                           '`Nachrichten senden` `Links einbetten` `Datein anhängen`'
                                           '`Externe Emojis verwenden`')
    await msg.delete()


class StandardButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Klicke mich",
            style=discord.enums.ButtonStyle.blurple,
            custom_id="interaction:DefaultButton"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Yeyy! Du hast mich angeklickt.", ephemeral=True)


class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            emby = discord.Embed(description=page)
            await destination.send(embed=emby)


############################################################

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            debug_guilds=[615901690536787983],
            command_prefix=get_prefix,
            help_command=MyNewHelp(),
            intents=discord.Intents.all()
        )

    async def on_ready(self):
        print(f"{bot.user} is ready and online!")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f"!help"))

    async def on_message(self, msg: Message):
        if msg.author.bot:
            return
        if not msg.content.startswith('!'):
            if get_globalChat(msg.guild.id, msg.channel.id):
                await sendAll(msg)
        if bot.user.mentioned_in(msg) and len(msg.content):
            await msg.channel.send(f'Mein Prefix hier: `{await get_prefix(bot, msg)}`', delete_after=15)
        await self.process_commands(msg)

    async def on_member_join(self, member):
        guild: Guild = member.guild
        if not member.bot:
            embed = Embed(title=f"Willkommen auf {guild.name}, {member.name}",
                                  description="Wir heißen dich herzlich Willkommen auf unserem Server! \n"
                                              "Bitte lies dir die Regeln durch um weiteren Zugriff zu erhalten",
                                  colour=0x22a7f0)
            try:
                if not member.dm_channel:
                    await member.create_dm()
                await member.dm_channel.send(embed=embed)
            except discord.errors.Forbidden:
                print(f"Es konnte keine Willkommensnachricht an {member.mention} gesendet werden.")
        else:
            autoguild = AUTOROLE.get(guild.id)
            if autoguild and autoguild["botrole"]:
                for roleId in autoguild["botrole"]:
                    role = guild.get_role(roleId)
                    if role:
                        await member.add_roles(role)
                        channel: TextChannel = discord.utils.get(member.guild.channels, id=615901690985447448)
                        await draw_card_welcome(channel, member, True)

    async def on_member_remove(self, member):
        pass

    async def on_guild_join(self, guild):
        prefixes = read_json("prefix")
        prefixes[str(guild.id)] = "!"
        write_json(prefixes, "prefix")

    async def on_guild_remove(self, guild):
        prefixes = read_json("prefix")
        prefixes.pop(str(guild.id))
        write_json(prefixes, "prefix")

    async def on_raw_reaction_add(self, payload):
        guild = bot.get_guild(payload.guild_id)
        payload_message_id = payload.message_id
        target_message_id = 877892113185001553
        channel = discord.utils.get(guild.channels, id=876149141435187221)
        if payload_message_id == target_message_id:
            if payload.emoji.name == "accepted":
                autoguild = AUTOROLE.get(guild.id)
                if autoguild and autoguild["memberrole"]:
                    for roleId in autoguild["memberrole"]:
                        role = guild.get_role(roleId)
                        if role:
                            await payload.member.add_roles(role)
                            await channel.send(
                                embed=Embed(description=f"Ich habe {payload.member.mention} die Rolle"
                                                        f" ***{role}*** hinzugefügt. Zugriff gestattet.")
                                , delete_after=10)

    async def on_raw_reaction_remove(self, payload):
        guild = bot.get_guild(payload.guild_id)
        channel = discord.utils.get(guild.channels, id=876149141435187221)
        member = discord.utils.find(lambda m: m.id == payload.user_id, guild.members)
        payload_message_id = payload.message_id
        target_message_id = 877892113185001553

        if payload_message_id == target_message_id:
            if payload.emoji.name == "accepted":
                autoguild = AUTOROLE.get(guild.id)
                if autoguild and autoguild["memberrole"]:
                    for roleId in autoguild["memberrole"]:
                        role = guild.get_role(roleId)
                        if role:
                            await member.remove_roles(role)
                            await channel.send(embed=Embed(description=f"Ich habe von {member.mention} die Rolle "
                                                                       f"***{role}*** entfernt. \n "
                                                                       "**Zugriff verweigert!**"),
                                               delete_after=10)

############################################################


#################### Bot initialisieren ####################

# bot = commands.Bot(debug_guilds=[615901690536787983], command_prefix='!')
bot = Bot()


def main():
    print("lade Erweiterungen ...")
    load_extensions()
    print(f"-----")
    bot.run(os.getenv('TOKEN'))

############################################################


if __name__ == "__main__":
    main()
