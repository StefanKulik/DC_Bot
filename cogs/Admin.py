import discord
from discord import app_commands
from discord.ext import commands

from config.Environment import PREFIX_LIST, COG_HANDLER, SERVER_INVITE
from config.Util import handle_app_command_error, send_interaction_message, is_not_pinned, get_modules

PREFIX_CHOICES = [app_commands.Choice(name=prefix, value=prefix) for prefix in PREFIX_LIST]
PROTECTED_CHANNEL_ID = 615901690985447448
FUNCTION_CHOICES = [app_commands.Choice(name=value, value=value) for value in COG_HANDLER]
MODULE_CHOICES = [app_commands.Choice(name=value, value=value) for value in get_modules()]

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="changeprefix", description="Prefix aendern")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(prefix="Neuer Prefix")
    @app_commands.choices(prefix=PREFIX_CHOICES)
    async def changeprefix(self, interaction: discord.Interaction, prefix: str) -> None:
        if interaction.guild is None:
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return
        if self.bot.db is None:
            await send_interaction_message(interaction, content="Die Datenbank ist aktuell nicht verfuegbar.", ephemeral=True)
            return

        await self.bot.db.set_prefix(interaction.guild.id, prefix)
        embed = discord.Embed(
            title=f"Prefix geaendert zu '{prefix}'",
            description="Schreibe /changeprefix <prefix> zum erneuten Aendern.",
        )
        await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)

    @app_commands.command(name="clear", description="Nachrichten im Channel loeschen")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(num="Anzahl der zu loeschenden Nachrichten")
    async def clear(self, interaction: discord.Interaction, num: app_commands.Range[int, 1, 100] = 10) -> None:
        channel = interaction.channel
        if interaction.guild is None or not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur in Textkanaelen.",
                                           ephemeral=True)
            return

        if channel.id == PROTECTED_CHANNEL_ID:
            embed = discord.Embed(description="Dieser Channel darf nicht geleert werden!")
            await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)
            return

        deleted_messages = await channel.purge(limit=int(num), check=is_not_pinned)
        embed = discord.Embed(description=f"**{len(deleted_messages)}** Nachrichten geloescht.")
        await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)

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

    @app_commands.command(name="kick", description="Member vom Server kicken")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(member="Mitglied", reason="Grund fuer den Kick")
    async def kick(
            self,
            interaction: discord.Interaction,
            member: discord.Member,
            reason: str | None = None,
    ) -> None:
        if interaction.guild is None:
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur auf einem Server.",
                                           ephemeral=True)
            return

        kick_reason = reason or "LOL"
        await member.kick(reason=kick_reason)

        embed = discord.Embed(title=f"Member {member.name} gekickt! Grund: {kick_reason}")
        await send_interaction_message(interaction, embed=embed, ephemeral=True, delete_after=5)

        if member.bot:
            return

        dm_embed = discord.Embed(title=f"Du wurdest von {interaction.guild.name} gekickt!")
        dm_embed.add_field(name="Grund", value=kick_reason, inline=False)
        try:
            if member.dm_channel is None:
                await member.create_dm()
            await member.dm_channel.send(embed=dm_embed)
            await member.dm_channel.send(SERVER_INVITE)
        except discord.Forbidden:
            print(f"Es konnte keine Nachricht an {member.mention} gesendet werden.")

    @app_commands.command(name="setautorole", description="Rollen in der DB hinterlegen")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(memberrole="Rolle fuer Member", botrole="Rolle fuer Bots")
    async def setautorole(
            self,
            interaction: discord.Interaction,
            memberrole: discord.Role,
            botrole: discord.Role,
    ) -> None:
        if interaction.guild is None:
            await send_interaction_message(interaction, content="Dieser Befehl funktioniert nur auf einem Server.",
                                           ephemeral=True)
            return
        if self.bot.db is None:
            await send_interaction_message(interaction, content="Die Datenbank ist aktuell nicht verfuegbar.",
                                           ephemeral=True)
            return

        await self.bot.db.set_autorole(interaction.guild.id, memberrole.id, botrole.id)
        await send_interaction_message(interaction, content="Autorole hinzugefuegt.", ephemeral=True)

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        await handle_app_command_error(interaction, error)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
