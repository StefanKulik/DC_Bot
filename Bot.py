import asyncio

import discord
from discord.ext import commands

from config.Environment import OWNER, TOKEN, VERSION
from config.Util import RoleButton, create_db_pool, draw_card_welcome, get_autorole, get_prefix, load_extensions, set_prefix


WELCOME_CHANNEL_ID = 615901690985447448


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix=set_prefix,
            owner_id=OWNER,
            intents=discord.Intents.all(),
            help_command=None,
        )

    async def setup_hook(self) -> None:
        print("lade Erweiterungen ...")
        await create_db_pool(self)
        await load_extensions(self)
        verification_view = discord.ui.View(timeout=None)
        verification_view.add_item(RoleButton(self))
        self.add_view(verification_view)
        await self.tree.sync()
        print("-----")

    async def close(self) -> None:
        db = getattr(self, "db", None)
        if db is not None:
            await db.close()
        await super().close()

    async def on_ready(self) -> None:
        print(f"{self.user} is ready and online!")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{VERSION} by peet_tea",
            )
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.user and self.user.mentioned_in(message) and message.content:
            await message.channel.send(f"Mein Prefix hier: `{await get_prefix(self, message)}`", delete_after=15)
        await self.process_commands(message)

    async def on_member_join(self, member: discord.Member) -> None:
        guild = member.guild
        if not member.bot:
            embed = discord.Embed(
                title=f"Willkommen auf {guild.name}, {member.name}",
                description=(
                    "Wir heissen dich herzlich willkommen auf unserem Server!\n"
                    "Bitte lies dir die Regeln durch, um weiteren Zugriff zu erhalten."
                ),
                colour=0x22A7F0,
            )
            try:
                if member.dm_channel is None:
                    await member.create_dm()
                await member.dm_channel.send(embed=embed)
            except discord.Forbidden:
                print(f"Es konnte keine Willkommensnachricht an {member.mention} gesendet werden.")

            welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
            if isinstance(welcome_channel, discord.TextChannel):
                embed = discord.Embed(
                    title="Herzlich Willkommen",
                    description=f"{member.mention}, willkommen auf **{guild.name}**",
                    colour=0x22A7F0,
                )
                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
                await welcome_channel.send(embed=embed, delete_after=30)
                await draw_card_welcome(welcome_channel, member)
            return

        role_id = await get_autorole(self, member, guild)
        role = guild.get_role(role_id) if role_id else None
        if role:
            await member.add_roles(role)
            welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
            if isinstance(welcome_channel, discord.TextChannel):
                await draw_card_welcome(welcome_channel, member, True)


async def main() -> None:
    bot = Bot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
