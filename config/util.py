import json
import os
import io
import pathlib
import discord

from pathlib import Path
from discord import Forbidden, TextChannel, Embed, ButtonStyle, Interaction
from discord import Member, File
from PIL import Image, ImageDraw, ImageFont


# Buttons #
class RoleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label='Verifiziere dich hier!',
            style=ButtonStyle.blurple,
            custom_id='interaction:RoleButton'
        )

    async def callback(self, interaction: Interaction):
        user = interaction.user
        role = interaction.guild.get_role(873637097951625216)

        if role is None:
            return
        if role not in user.roles:
            await user.add_roles(role)
            await interaction.response.send_message(f'🎉 Du bist nun verifiziert!', ephemeral=True)
        else:
            await interaction.response.send_message(f'❌ Du bist bereits verifiziert!', ephemeral=True)


class StandardButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Klicke mich",
            style=discord.enums.ButtonStyle.blurple,
            custom_id="interaction:DefaultButton"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Yeyy! Du hast mich angeklickt.", ephemeral=True)


# allgemein #
async def get_prefix(msg):
    prefixes = read_json("prefix")
    return prefixes[str(msg.guild.id)]


def is_not_pinned(mess):
    return not mess.pinned


# GlobalChat_Functions #
def get_servers():
    if os.path.isfile("config/servers.json"):
        servers = read_json("servers")
    else:
        servers = {"servers": []}
        write_json(servers, "servers")
    return servers


def get_globalChat(guild_id, channel_id=None):
    global_chat = None
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["guildid"]) == int(guild_id):
            if channel_id:
                if server["channelid"] == int(channel_id):
                    global_chat = server
            else:
                global_chat = server
    return global_chat


def get_globalChat_id(guild_id, channel_id=None):  # gibt die id des globalchats wieder
    global_chat = get_globalChat(guild_id, channel_id=None)
    if channel_id:
        return channel_id
    return global_chat["channelid"]


def get_globalChat_index(guild_id):  # gibt index für server in servers wieder
    index = -1
    i = 0
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["guildid"]) == guild_id:
            index = i
        i += 1
    return index


def isGlobalChat(channel_id):  # ist dieser channel der globalchat?
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["channelid"]) == int(channel_id):
            return True
    return False


def globalchatExists(guild_id):  # hat der server einen globalchat?
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["guildid"]) == int(guild_id):
            return True
    return False
############################################################


# json functions #
def get_path():
    """
    A function to get the current path to bot.py
    Returns:
     - cwd (string) : Path to bot.py directory
    """
    cwd = Path(__file__).parents[1]
    cwd = str(cwd)
    return cwd


def read_json(filename):
    """
    A function to read a json file and return the data.
    Params:
     - filename (string) : The name of the file to open
    Returns:
     - data (dict) : A dict of the data in the file
    """
    cwd = get_path()
    with open(cwd + "/config/" + filename + ".json", "r") as file:
        data = json.load(file)
    return data


def write_json(data, filename):
    """
    A function used to write data to a json file
    Params:
     - data (dict) : The data to write to the file
     - filename (string) : The name of the file to write to
    """
    cwd = get_path()
    with open(cwd + "/config/" + filename + ".json", "w") as file:
        json.dump(data, file, indent=4)
############################################################


# embeds #
async def send_embed(ctx, emb: Embed, num: int = None, channel: TextChannel = None):
    try:
        if num:
            await ctx.send(embed=emb, delete_after=num)
        elif channel:
            await channel.send(embed=emb)
        elif num and channel:
            await channel.send(embed=emb, delete_after=num)
        else:
            await ctx.send(embed=emb)
    except Forbidden:
        try:
            await ctx.send("Hey, scheint, als ob ich kein Embed senden kann. Bitte überprüfe meine Berechtigungen :)")
        except Forbidden:
            await ctx.author.send(
                f"Hey, scheint, als könnte ich in {ctx.channel.name} auf {ctx.guild.name} keine Nachrichten senden\n"
                f"Magst du das Server Team benachrichtigen? :slight_smile: ", embed=emb)


async def error_embed(ctx, com: str, des: str):
    e = discord.Embed(title=f"{com} error", description=des)
    e.set_thumbnail(url="https://cdn.discordapp.com/emojis/751739197009690655.gif?v=1")
    await send_embed(ctx, e, 5)
############################################################


# welcome card #
if os.path.isfile("Discord_Bot/config/blankcard.jpg"):
    blank_card = pathlib.Path("Discord_Bot/config/blankcard.jpg")  #  for heroku
else:
    blank_card = pathlib.Path("config/blankcard.jpg")  # for pycharm

background_image = Image.open(blank_card)
background_image = background_image.convert('RGBA')


async def draw_card_welcome(channel, member: Member, bot: bool = None):
    size = 256
    avatar_size = 240

    image = background_image.copy()
    image_width, image_height = image.size

    margin_left = 55
    margin_top = 25
    margin_right = image_width - 55
    margin_bottom = image_height - 25

    rect_width = margin_right - margin_left
    rect_height = margin_bottom - margin_top

    draw = ImageDraw.Draw(image)

    if bot:
        text = f'BOT {member} ist dem Server beigetreten'
    else:
        text = f'{member} ist dem Server beigetreten'
    avatar_asset = member.avatar
    # avatar_asset = member.avatar_url_as(format='jpg', size=SIZE)

    buffer_avatar = io.BytesIO(await avatar_asset.read())

    avatar_image = Image.open(buffer_avatar)

    avatar_image = avatar_image.resize((avatar_size, avatar_size))

    circle_image = Image.new('L', (avatar_size, avatar_size))
    circle_draw = ImageDraw.Draw(circle_image)
    circle_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

    avatar_start_x = (rect_width // 2) + margin_left - (avatar_size // 2)
    avatar_start_y = margin_top + 45
    image.paste(avatar_image, (avatar_start_x, avatar_start_y), circle_image)

    if os.path.isfile("Discord_Bot/arial.ttf"):
        font_datei = "Discord_Bot/arial.ttf"
    else:
        font_datei = "arial.ttf"
    font = ImageFont.truetype(font_datei, 40)  # for heroku
    # font = ImageFont.truetype('arial.ttf', 40)

    text_width, text_height = draw.textsize(text, font=font)
    text_start_x = (rect_width // 2) + margin_left - (text_width // 2)
    text_start_y = rect_height - 85

    draw.text((text_start_x, text_start_y), text, fill=(255, 255, 255, 255), font=font)

    buffer_output = io.BytesIO()

    image.save(buffer_output, format='PNG')

    buffer_output.seek(0)

    await channel.send(file=File(buffer_output, f'welcome-card.png'))
############################################################


async def member_channel(member):
    guild = member.guild
    channel = discord.utils.get(guild.channels, id=877689459804622869)
    await channel.edit(name=f'Mitglieder: {guild.member_count}')
