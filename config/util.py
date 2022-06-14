import io
import pathlib
import discord

from discord import Forbidden, TextChannel, Embed, ButtonStyle, Interaction, Member, File
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from config.envirorment import DEFAULT_PREFIX


########################## Button ##########################

class RoleButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(
            label='Verifiziere dich hier!',
            style=ButtonStyle.blurple,
            custom_id='interaction:RoleButton'
        )
        self.bot = bot

    async def callback(self, interaction: Interaction):
        user = interaction.user
        role = interaction.guild.get_role(await get_autorole(self.bot, user, interaction.guild))
        if role is None:
            await interaction.response.send_message(f'🎉Verifizierung fehlgeschlagen!', ephemeral=True)
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


############################################################


########################## common ##########################

def is_not_pinned(mess):
    return not mess.pinned


async def set_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot, message)
    prefix = await bot.db.fetch('SELECT prefix FROM guilds WHERE guild_id = $1', message.guild.id)
    if len(prefix) == 0:
        await bot.db.execute(f'INSERT INTO guilds(guild_id, prefix) VALUES($1, $2)', message.guild.id, DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    else:
        prefix = prefix[0].get('prefix')
    return commands.when_mentioned_or(prefix)(bot, message)


async def get_prefix(bot, message):
    prefix = await bot.db.fetch('SELECT prefix FROM guilds WHERE guild_id = $1', message.guild.id)
    if len(prefix) == 0:
        await bot.db.execute(f'INSERT INTO guilds(guild_id, prefix) VALUES($1, $2)', message.guild.id, DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    else:
        prefix = prefix[0].get('prefix')
    return prefix


############################################################


#################### Autorole functions ####################

async def get_autorole(bot, member, guild):
    if not member.bot:
        role_id = await bot.db.fetch('SELECT memberrole_id FROM autorole WHERE guild_id = $1', guild.id)
        return role_id[0].get('memberrole_id')
    else:
        role_id = await bot.db.fetch('SELECT botrole_id from autorole WHERE guild_id = $1', guild.id)
        return role_id[0].get('botrole_id')


############################################################


################### Globalchat functions ################### #TODO: auf DB Abfragen umstellen

async def get_servers(bot):
    return await bot.db.fetch('SELECT * FROM globalchat')


async def get_globalchat(bot, guild_id):
    return await bot.db.fetch('SELECT * FROM globalchat WHERE guild_id = $1', guild_id)


# async def get_globalchat_id(bot, guild_id, channel_id=None):  # gibt die id des globalchats wieder
#     global_chat = get_globalchat(bot, guild_id, channel_id=None)
#     if channel_id:
#         return channel_id
#     return global_chat["channel_id"]
#
async def is_globalchat(self, guild_id, channel_id):  # ist dieser channel der globalchat?
    return channel_id == (await self.db.fetch('SELECT channel_id FROM globalchat WHERE guild_id = $1', guild_id))[0]['channel_id']


async def globalchat_exists(self, guild_id):  # hat der server einen globalchat?
    return len(await self.bot.db.fetch('SELECT guild_id FROM globalchat WHERE guild_id = $1', guild_id)) != 0


############################################################


########################## embeds ##########################
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


####################### welcome card #######################
blank_card = pathlib.Path("config/blankcard.jpg")
background_image = Image.open(blank_card)
background_image = background_image.convert('RGBA')


async def draw_card_welcome(channel, member: Member, bot: bool = None):
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

    buffer_avatar = io.BytesIO(await avatar_asset.read())

    avatar_image = Image.open(buffer_avatar)

    avatar_image = avatar_image.resize((avatar_size, avatar_size))

    circle_image = Image.new('L', (avatar_size, avatar_size))
    circle_draw = ImageDraw.Draw(circle_image)
    circle_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

    avatar_start_x = (rect_width // 2) + margin_left - (avatar_size // 2)
    avatar_start_y = margin_top + 45
    image.paste(avatar_image, (avatar_start_x, avatar_start_y), circle_image)

    font = ImageFont.truetype('config/arial.ttf', 40)  # for heroku

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
