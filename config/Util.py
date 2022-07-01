import io
import os
import pathlib
from datetime import datetime

import asyncpg
import discord
import pytz

from discord import Forbidden, TextChannel, Embed, ButtonStyle, Interaction, Member, File, Guild, Permissions, \
    ExtensionAlreadyLoaded, ExtensionNotLoaded
from discord.commands import SlashCommandGroup
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from config.Environment import DEFAULT_PREFIX, SERVER_INVITE, DATABASE_URL


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


########################## common ##########################
def is_not_pinned(mess):
    return not mess.pinned


def load_extensions(b):
    cog = "./cogs/"
    for o in os.listdir(cog):
        if not o.startswith("_"):
            for f in os.listdir(cog + o):
                if f.endswith(".py") and not f.startswith("_"):
                    b.load_extension(f"cogs.{o}.{f[:-3]}")
            print(f"Geladen '{o}'")


async def create_db_pool(b):
    print('connecting to database ...')
    b.db = await asyncpg.create_pool(dsn=DATABASE_URL)
    print('Database connection successful ...')
    print('-----')


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


async def get_prefix_context(bot, ctx):
    prefix = await bot.db.fetch('SELECT prefix FROM guilds WHERE guild_id = $1', ctx.guild.id)
    if len(prefix) == 0:
        await bot.db.execute(f'INSERT INTO guilds(guild_id, prefix) VALUES($1, $2)', ctx.guild.id, DEFAULT_PREFIX)
        prefix = DEFAULT_PREFIX
    else:
        prefix = prefix[0].get('prefix')
    return prefix


async def send_all(b, msg):
    servers = []
    for server in await get_servers(b):
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
    globalchat = await get_globalchat(b, msg.guild.id)

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
        gc = await get_globalchat(b, server)
        g: Guild = b.get_guild(gc[0]['guild_id'])
        if g:
            c: TextChannel = g.get_channel(gc[0]['channel_id'])
            if c:
                permissions: Permissions = c.permissions_for(g.get_member(b.user.id))
                if permissions.send_messages:
                    if permissions.embed_links and permissions.attach_files and permissions.external_emojis:
                        await c.send(embed=embed)
                    else:
                        await c.send('{0}: {1}'.format(author.name, content))
                        await c.send('Es fehlen einige Berechtigungen. '
                                     '`Nachrichten senden` `Links einbetten` `Dateien anhängen`'
                                     '`Externe Emojis verwenden`')
    await msg.delete()


#################### Autorole functions ####################
async def get_autorole(bot, member, guild):
    if not member.bot:
        role_id = await bot.db.fetch('SELECT memberrole_id FROM autorole WHERE guild_id = $1', guild.id)
        return role_id[0].get('memberrole_id')
    else:
        role_id = await bot.db.fetch('SELECT botrole_id from autorole WHERE guild_id = $1', guild.id)
        return role_id[0].get('botrole_id')


################### Globalchat functions ###################

async def get_servers(bot):
    return await bot.db.fetch('SELECT * FROM globalchat')


async def get_globalchat(bot, guild_id):
    return await bot.db.fetch('SELECT * FROM globalchat WHERE guild_id = $1', guild_id)


async def is_globalchat(self, guild_id, channel_id):  # ist dieser channel der globalchat?
    return channel_id == (await self.db.fetch('SELECT channel_id FROM globalchat WHERE guild_id = $1', guild_id))[0][
        'channel_id']


async def globalchat_exists(self, guild_id):  # hat der server einen globalchat?
    return len(await self.bot.db.fetch('SELECT guild_id FROM globalchat WHERE guild_id = $1', guild_id)) != 0


################### Admin functions ###################
# TODO: Auf neue Ordner Struktur anpassen
def get_modules():
    modules = []
    for file in os.listdir("./cogs"):
        if file.endswith(".py") and not file.startswith("_"):
            modules.append(file[:-3])
    return modules


async def load(self, ctx, module: str):
    if module is None:
        for cog in get_modules():
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
        for cog in get_modules():
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
        for cog in get_modules():
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


########################  Games Functions  #########################
async def delete_thread(ctx, mode: str, member: Member = None):
    if mode == 'ttt':
        threads = ctx.guild.get_channel(876278253025914911).threads
        for thread in threads:
            if thread.name == f"ttt-{ctx.author.name.lower().replace(' ', '_')}-{member.name.lower().replace(' ', '_')}":
                await thread.delete()
    elif mode == 'rps':
        threads = ctx.guild.get_channel(876278221878992916).threads
        for thread in threads:
            if thread.name == 'ssp-' + ctx.author.name.lower().replace(' ', '_'):
                await thread.delete()


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


####################### welcome card #######################
blank_card = pathlib.Path("config/img/blankcard.jpg")
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
