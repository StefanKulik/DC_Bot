import json
import os
import io
import pathlib

import discord
import urllib.request

from pathlib import Path
from discord import Forbidden, TextChannel, Embed
from discord import Member, File
from PIL import Image, ImageDraw, ImageFont


# allgemein #
async def get_prefix(bot, msg):
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


def get_globalChat(guildid, channelid=None):
    globalChat = None
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["guildid"]) == int(guildid):
            if channelid:
                if server["channelid"] == int(channelid):
                    globalChat = server
            else:
                globalChat = server
    return globalChat


def get_globalChat_id(guildid, channelid=None):  # gibt die id des globalchats wieder
    globalChat = get_globalChat(guildid, channelid=None)
    if channelid:
        return channelid
    return globalChat["channelid"]


def get_globalChat_index(guildid):  # gibt index für server in servers wieder
    index = -1
    i = 0
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["guildid"]) == guildid:
            index = i
        i += 1
    return index


def isGlobalChat(channelid):  # ist dieser channel der globalchat?
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["channelid"]) == int(channelid):
            return True
    return False


def globalchatExists(guildid):  # hat der server einen globalchat?
    servers = get_servers()
    for server in servers["servers"]:
        if int(server["guildid"]) == int(guildid):
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
    SIZE = 256
    AVATAR_SIZE = 240

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
    avatar_asset = member.avatar_url_as(format='jpg', size=SIZE)

    buffer_avatar = io.BytesIO(await avatar_asset.read())

    avatar_image = Image.open(buffer_avatar)

    avatar_image = avatar_image.resize((AVATAR_SIZE, AVATAR_SIZE))

    circle_image = Image.new('L', (AVATAR_SIZE, AVATAR_SIZE))
    circle_draw = ImageDraw.Draw(circle_image)
    circle_draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)

    avatar_start_x = (rect_width // 2) + margin_left - (AVATAR_SIZE // 2)
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

