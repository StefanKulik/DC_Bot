import discord
import asyncio
from pathlib import Path
from discord.ext import commands
from config.Environment import TOKEN, VERSION, OWNER
from config.SqliteStore import create_db_pool


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
        print(f"loaded '{extension}'")


class Bot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",
            owner_id=OWNER,
            intents=discord.Intents.all(),
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await create_db_pool(self)
        print("load extensions ...")
        await load_extensions(self)
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
                name=f"Version {VERSION}",
            )
        )

async def main() -> None:
    bot = Bot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
