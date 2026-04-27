import io
from pathlib import Path

import asyncpg
import discord

from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from config.Environment import DATABASE_URL, DEFAULT_PREFIX


class RoleButton(discord.ui.Button):
    def __init__(self, bot: commands.Bot):
        super().__init__(
            label="Verifiziere dich hier!",
            style=discord.ButtonStyle.blurple,
            custom_id="interaction:RoleButton",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        user = interaction.user
        role_id = await get_autorole(self.bot, user, interaction.guild)
        role = interaction.guild.get_role(role_id) if role_id else None
        if role is None:
            await interaction.response.send_message("Verifizierung fehlgeschlagen!", ephemeral=True)
            return

        if role not in user.roles:
            await user.add_roles(role)
            await interaction.response.send_message("Du bist nun verifiziert!", ephemeral=True)
            return

        await interaction.response.send_message("Du bist bereits verifiziert!", ephemeral=True)


class StandardButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Klicke mich",
            style=discord.ButtonStyle.blurple,
            custom_id="interaction:DefaultButton",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Yeyy! Du hast mich angeklickt.", ephemeral=True)


def is_not_pinned(message: discord.Message) -> bool:
    return not message.pinned


def iter_extension_names() -> list[str]:
    extensions: list[str] = []
    cogs_dir = Path("cogs")
    for category in sorted(cogs_dir.iterdir()):
        if not category.is_dir() or category.name.startswith("_"):
            continue
        for file in sorted(category.glob("*.py")):
            if file.stem.startswith("_"):
                continue
            extensions.append(f"cogs.{category.name}.{file.stem}")
    return extensions


def get_modules() -> list[str]:
    return [extension.removeprefix("cogs.") for extension in iter_extension_names()]


async def load_extensions(bot: commands.Bot) -> None:
    for extension in iter_extension_names():
        await bot.load_extension(extension)
        print(f"Geladen '{extension}'")


async def create_db_pool(bot: commands.Bot) -> None:
    print("Connect to database...")
    try:
        bot.db = await asyncpg.create_pool(
            dsn=DATABASE_URL,
            min_size=1,
            max_size=5,
            command_timeout=30,
            server_settings={"search_path": "discord"},
        )
    except Exception as exc:
        bot.db = None
        print(f"Database unavailable, continuing without DB features: {type(exc).__name__}: {exc}")
    else:
        print("Connection successful")


async def _resolve_prefix(bot: commands.Bot, guild_id: int) -> str:
    db = getattr(bot, "db", None)
    if db is None:
        return DEFAULT_PREFIX

    try:
        prefix = await db.fetch("SELECT prefix FROM guilds WHERE guild_id = $1", guild_id)
        if len(prefix) == 0:
            await db.execute("INSERT INTO guilds(guild_id, prefix) VALUES($1, $2)", guild_id, DEFAULT_PREFIX)
            return DEFAULT_PREFIX
        return prefix[0].get("prefix", DEFAULT_PREFIX)
    except Exception:
        return DEFAULT_PREFIX


async def set_prefix(bot: commands.Bot, message: discord.Message):
    if not message.guild:
        return commands.when_mentioned_or(DEFAULT_PREFIX)(bot, message)
    prefix = await _resolve_prefix(bot, message.guild.id)
    return commands.when_mentioned_or(prefix)(bot, message)


async def get_prefix(bot: commands.Bot, message: discord.Message) -> str:
    return await _resolve_prefix(bot, message.guild.id)


async def get_prefix_context(bot: commands.Bot, ctx) -> str:
    return await _resolve_prefix(bot, ctx.guild.id)


async def get_autorole(bot: commands.Bot, member: discord.Member, guild: discord.Guild) -> int | None:
    db = getattr(bot, "db", None)
    if db is None:
        return None

    try:
        if not member.bot:
            role_id = await db.fetchrow("SELECT memberrole_id FROM autorole WHERE guild_id = $1", guild.id)
            return role_id.get("memberrole_id") if role_id else None

        role_id = await db.fetchrow("SELECT botrole_id FROM autorole WHERE guild_id = $1", guild.id)
        return role_id.get("botrole_id") if role_id else None
    except Exception:
        return None


async def handle_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await send_interaction_message(
            interaction,
            content="You need administrator permissions!",
            ephemeral=True,
            delete_after=3,
        )
        return
    raise error


async def send_interaction_message(
    interaction: discord.Interaction,
    *,
    content: str | None = None,
    embed: discord.Embed | None = None,
    ephemeral: bool = False,
    delete_after: float | None = None,
    view: discord.ui.View | None = None,
) -> None:
    kwargs = {
        "content": content,
        "embed": embed,
        "ephemeral": ephemeral,
        "delete_after": delete_after,
        "view": view,
    }
    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


async def delete_thread(ctx, mode: str, member: discord.Member | None = None) -> None:
    if mode == "ttt":
        threads = ctx.guild.get_channel(1496504118884434042).threads
        for thread in threads:
            expected_name = f"ttt-{ctx.author.name.lower().replace(' ', '_')}-{member.name.lower().replace(' ', '_')}"
            if thread.name == expected_name:
                await thread.delete()
    elif mode == "rps":
        threads = ctx.guild.get_channel(1496504095379427479).threads
        for thread in threads:
            if thread.name == f"ssp-{ctx.author.name.lower().replace(' ', '_')}":
                await thread.delete()


async def send_embed(
    ctx,
    embed: discord.Embed,
    delete_after: int | None = None,
    channel: discord.abc.Messageable | None = None,
) -> None:
    target = channel or ctx
    try:
        await target.send(embed=embed, delete_after=delete_after)
    except discord.Forbidden:
        try:
            await ctx.send("Hey, scheint, als ob ich kein Embed senden kann. Bitte ueberpruefe meine Berechtigungen :)")
        except discord.Forbidden:
            await ctx.author.send(
                f"Hey, scheint, als koennte ich in {ctx.channel.name} auf {ctx.guild.name} keine Nachrichten senden.\n"
                "Magst du das Server-Team benachrichtigen?",
                embed=embed,
            )


async def error_embed(ctx, command_name: str, description: str) -> None:
    embed = discord.Embed(title=f"{command_name} error", description=description)
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/751739197009690655.gif?v=1")
    await send_embed(ctx, embed, delete_after=5)


BACKGROUND_IMAGE = Image.open(Path("config/img/blankcard.jpg")).convert("RGBA")
FONT_PATH = Path("config/font/arial.ttf")


async def draw_card_welcome(channel, member: discord.Member, bot: bool = False) -> None:
    avatar_size = 240
    image = BACKGROUND_IMAGE.copy()
    image_width, image_height = image.size

    margin_left = 55
    margin_top = 25
    margin_right = image_width - 55
    margin_bottom = image_height - 25

    rect_width = margin_right - margin_left
    rect_height = margin_bottom - margin_top

    draw = ImageDraw.Draw(image)
    text = f"BOT {member} ist dem Server beigetreten" if bot else f"{member} ist dem Server beigetreten"

    avatar_asset = member.display_avatar
    buffer_avatar = io.BytesIO(await avatar_asset.read())
    avatar_image = Image.open(buffer_avatar).resize((avatar_size, avatar_size))

    circle_image = Image.new("L", (avatar_size, avatar_size))
    circle_draw = ImageDraw.Draw(circle_image)
    circle_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

    avatar_start_x = (rect_width // 2) + margin_left - (avatar_size // 2)
    avatar_start_y = margin_top + 45
    image.paste(avatar_image, (avatar_start_x, avatar_start_y), circle_image)

    font = ImageFont.truetype(str(FONT_PATH), 40)
    text_box = draw.textbbox((0, 0), text, font=font)
    text_width = text_box[2] - text_box[0]
    text_start_x = (rect_width // 2) + margin_left - (text_width // 2)
    text_start_y = rect_height - 85

    draw.text((text_start_x, text_start_y), text, fill=(255, 255, 255, 255), font=font)

    buffer_output = io.BytesIO()
    image.save(buffer_output, format="PNG")
    buffer_output.seek(0)

    await channel.send(file=discord.File(buffer_output, "welcome-card.png"))
