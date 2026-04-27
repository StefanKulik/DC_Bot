import discord
from discord import app_commands
from discord.ext import commands

from config.Environment import COG_HANDLER
from config.Util import get_modules, handle_app_command_error, send_interaction_message


FUNCTION_CHOICES = [app_commands.Choice(name=value, value=value) for value in COG_HANDLER]
MODULE_CHOICES = [app_commands.Choice(name=value, value=value) for value in get_modules()]


class CogHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="cog", description="Cog load, unload, reload")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(function="Aktion", module="Betroffenes Modul")
    @app_commands.choices(function=FUNCTION_CHOICES, module=MODULE_CHOICES)
    async def handler(
        self,
        interaction: discord.Interaction,
        function: str,
        module: str | None = None,
    ) -> None:
        targets = [module] if module else get_modules()
        results: list[str] = []

        for target in targets:
            extension_name = f"cogs.{target}"
            try:
                if function == "load":
                    await self.bot.load_extension(extension_name)
                elif function == "unload":
                    await self.bot.unload_extension(extension_name)
                else:
                    await self.bot.reload_extension(extension_name)
            except commands.ExtensionAlreadyLoaded:
                results.append(f"{target}: bereits geladen")
            except commands.ExtensionNotLoaded:
                results.append(f"{target}: nicht geladen")
            except commands.ExtensionError as exc:
                results.append(f"{target}: {type(exc).__name__}: {exc}")
            else:
                results.append(f"{target}: OK")

        await self.bot.tree.sync()

        embed = discord.Embed(
            title=f"Cog {function}",
            description="\n".join(results) if results else "Keine Module verarbeitet.",
            colour=discord.Colour.blurple(),
        )
        await send_interaction_message(interaction, embed=embed, ephemeral=True)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CogHandler(bot))
