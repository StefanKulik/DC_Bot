import discord
from discord.ext import commands

from config.Environment import BOT, OWNER, VERSION
from config.Util import get_prefix


def command_aliases(command: commands.Command) -> str:
    if command.aliases:
        return "Aliases: " + ", ".join(command.aliases)
    return ""


def command_params(command: commands.Command) -> str:
    params = []
    for key, value in command.params.items():
        if key not in {"self", "ctx"}:
            params.append(f"[{key}]" if "None" in str(value) else f"<{key}>")
    return " ".join(params)


class Help(commands.Cog, description="Zeigt diese Help-Nachricht an"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def get_cog_app_commands(self, cog_name: str):
        app_commands = []
        for command in self.bot.tree.walk_commands():
            binding = getattr(command, "binding", None)
            if binding is not None and binding.__class__.__name__ == cog_name:
                app_commands.append(command)
        return app_commands

    @commands.command(name="help", description="Zeigt alle Module dieses Bots an", help="help [Modul]")
    async def help(self, ctx: commands.Context, *requested: str) -> None:
        prefix = await get_prefix(self.bot, ctx.message)

        owner_member = ctx.guild.get_member(OWNER) if ctx.guild else None
        bot_member = ctx.guild.get_member(BOT) if ctx.guild else None
        owner_name = owner_member.name if owner_member else str(OWNER)
        bot_name = bot_member.name if bot_member else (self.bot.user.name if self.bot.user else "Bot")

        if not requested:
            embed = discord.Embed(
                title=f"{bot_name}s Hilfe",
                description=f"**`{prefix}help <Modul>`** fuer mehr Informationen ueber ein Modul.",
                color=discord.Color.blue(),
            )

            module_lines = []
            for cog_name, cog in self.bot.cogs.items():
                module_lines.append(f"`{cog_name}`\n*{cog.description or 'Keine Beschreibung'}*")
            if module_lines:
                embed.add_field(name="Module", value="\n\n".join(module_lines), inline=False)

            prefix_commands = []
            for command in self.bot.walk_commands():
                if command.cog_name is None and not command.hidden:
                    prefix_commands.append(f"`{prefix}{command.name}` - {command.description or 'Keine Beschreibung'}")
            if prefix_commands:
                embed.add_field(name="Prefix Commands", value="\n".join(prefix_commands), inline=False)

            slash_commands = []
            for command in self.bot.tree.walk_commands():
                slash_commands.append(f"`/{command.name}` - {command.description or 'Keine Beschreibung'}")
            if slash_commands:
                embed.add_field(name="App Commands", value="\n".join(slash_commands), inline=False)

            owner_display = owner_member.mention if owner_member else str(OWNER)
            embed.add_field(
                name="Ueber",
                value=(
                    f"Der Bot wird entwickelt von {owner_name}, basierend auf discord.py.\n"
                    f"Diese Version wird gepflegt von {owner_display}."
                ),
                inline=False,
            )
            embed.set_footer(text=f"Bot Version: V{VERSION}")
            await ctx.send(embed=embed)
            return

        if len(requested) > 1:
            embed = discord.Embed(
                title="Das ist zu viel.",
                description="Bitte frage nur ein Modul zur Zeit an.",
                color=discord.Color.orange(),
            )
            await ctx.send(embed=embed)
            return

        query = requested[0]

        if query in self.bot.cogs:
            prefix_lines = []
            for command in self.bot.get_cog(query).get_commands():
                if not command.hidden:
                    description = command.description or command.brief or "Keine Beschreibung"
                    prefix_lines.append(f"`{prefix}{command.name}` - {description}")

            app_lines = []
            for command in self.get_cog_app_commands(query):
                app_lines.append(f"`/{command.name}` - {command.description or 'Keine Beschreibung'}")

            description_parts = []
            if prefix_lines:
                description_parts.append("Prefix Commands:\n" + "\n".join(prefix_lines))
            if app_lines:
                description_parts.append("App Commands:\n" + "\n".join(app_lines))

            embed = discord.Embed(
                title=f"{query} - Befehle",
                description="\n\n".join(description_parts) or "Keine Befehle gefunden.",
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
            return

        for command in self.bot.commands:
            if command.name == query:
                description = command.description or "Keine Beschreibung"
                embed = discord.Embed(
                    description=(
                        f"{description}\n\n"
                        f"{prefix}{command.name} {command_params(command)}\n"
                        f"{command_aliases(command)}\n\n"
                        f"{command.help or ''}"
                    )
                )
                await ctx.send(embed=embed)
                return

        for command in self.bot.tree.walk_commands():
            if command.name == query:
                embed = discord.Embed(
                    title=f"/{command.name}",
                    description=command.description or "Keine Beschreibung",
                    color=discord.Color.green(),
                )
                await ctx.send(embed=embed)
                return

        embed = discord.Embed(
            title="Was ist das?!",
            description=f"Von `{query}` habe ich zuvor noch nichts gehoert.",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help(bot))
