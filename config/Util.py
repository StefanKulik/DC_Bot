import io
from pathlib import Path

import discord

from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

from config.Environment import DEFAULT_PREFIX
from config.SqliteStore import SqliteDatabase


class RoleButton(discord.ui.Button):
    def __init__(self, bot: commands.Bot):
        super().__init__(
            label="Verifiziere dich hier!",
            style=discord.ButtonStyle.blurple,
            custom_id="interaction:RoleButton",
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True)
            await self._verify_member(interaction)
        except Exception as exc:
            print(f"RoleButton failed: {type(exc).__name__}: {exc}")
            if interaction.response.is_done():
                await interaction.followup.send("Verifizierung fehlgeschlagen.", ephemeral=True)
            else:
                await interaction.response.send_message("Verifizierung fehlgeschlagen.", ephemeral=True)

    async def _verify_member(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Verifizierung funktioniert nur auf einem Server.", ephemeral=True)
            return

        member = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)
        if member is None:
            try:
                member = await guild.fetch_member(interaction.user.id)
            except discord.HTTPException:
                member = None

        if member is None:
            await interaction.followup.send("Verifizierung fehlgeschlagen: Member konnte nicht geladen werden.", ephemeral=True)
            return

        role_id = await get_autorole(self.bot, member, guild)
        role = guild.get_role(role_id) if role_id else None
        if role is None:
            await interaction.followup.send("Verifizierung fehlgeschlagen: Member-Rolle nicht gefunden.", ephemeral=True)
            return

        if role in member.roles:
            await interaction.followup.send("Du bist bereits verifiziert!", ephemeral=True)
            return

        bot_user = self.bot.user
        bot_member = guild.me
        if bot_member is None and bot_user is not None:
            bot_member = guild.get_member(bot_user.id)
        if bot_member is None and bot_user is not None:
            try:
                bot_member = await guild.fetch_member(bot_user.id)
            except discord.HTTPException:
                bot_member = None

        if bot_member is None:
            await interaction.followup.send("Verifizierung fehlgeschlagen: Bot-Member konnte nicht geladen werden.", ephemeral=True)
            return

        if not bot_member.guild_permissions.manage_roles:
            await interaction.followup.send(
                "Verifizierung fehlgeschlagen: Mir fehlt die Berechtigung `Rollen verwalten`.",
                ephemeral=True,
            )
            return

        if role >= bot_member.top_role:
            await interaction.followup.send(
                "Verifizierung fehlgeschlagen: Die Member-Rolle liegt ueber oder auf meiner hoechsten Rolle.",
                ephemeral=True,
            )
            return

        try:
            await member.add_roles(role, reason="Rule verification")
        except discord.Forbidden:
            await interaction.followup.send("Verifizierung fehlgeschlagen: Ich darf diese Rolle nicht vergeben.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.followup.send("Verifizierung fehlgeschlagen: Discord konnte die Rolle nicht setzen.", ephemeral=True)
            return

        await interaction.followup.send("Du bist nun verifiziert!", ephemeral=True)


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
    for file in sorted(cogs_dir.rglob("*.py")):
        relative_path = file.relative_to(cogs_dir)
        if "__pycache__" in relative_path.parts:
            continue
        if file.stem.startswith("_") or file.stem == "__init__":
            continue
        module_path = ".".join(("cogs", *relative_path.with_suffix("").parts))
        extensions.append(module_path)
    return extensions


def get_modules() -> list[str]:
    return [extension.removeprefix("cogs.") for extension in iter_extension_names()]


async def load_extensions(bot: commands.Bot) -> None:
    for extension in iter_extension_names():
        await bot.load_extension(extension)
        print(f"Geladen '{extension}'")


async def create_db_pool(bot: commands.Bot) -> None:
    print("Connect to SQLite database...")
    try:
        bot.db = SqliteDatabase("datenbank.db")
        await bot.db.connect()
    except Exception as exc:
        bot.db = None
        print(f"Database unavailable, continuing without DB features: {type(exc).__name__}: {exc}")
    else:
        print("SQLite database connected")


async def _resolve_prefix(bot: commands.Bot, guild_id: int) -> str:
    db = getattr(bot, "db", None)
    if db is None:
        return DEFAULT_PREFIX

    try:
        return await db.get_prefix(guild_id)
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
        return await db.get_autorole(guild.id, is_bot=member.bot)
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
