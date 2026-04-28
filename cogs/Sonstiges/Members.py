import discord
from discord import app_commands
from discord.ext import commands

from config.Util import get_prefix_context


class Members(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._context_menus: list[app_commands.ContextMenu] = []

    async def cog_load(self) -> None:
        self._context_menus = [
            app_commands.ContextMenu(name="Memberliste", callback=self.memberlist),
            app_commands.ContextMenu(name="Botliste", callback=self.botliste),
            app_commands.ContextMenu(name="Userinfo", callback=self.userinfo),
            app_commands.ContextMenu(name="Serverinfo", callback=self.serverinfo),
        ]
        for menu in self._context_menus:
            self.bot.tree.add_command(menu)

    async def cog_unload(self) -> None:
        for menu in self._context_menus:
            self.bot.tree.remove_command(menu.name, type=menu.type)

    async def memberlist(self, interaction: discord.Interaction, member: discord.Member | discord.User) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return

        member_list = [guild_member for guild_member in interaction.guild.members if not guild_member.bot]
        entries = "\n".join(guild_member.mention for guild_member in member_list) or "Keine Member gefunden."
        embed = discord.Embed(title=f"Member Liste (Anzahl: {len(member_list)})", description=entries)
        embed.set_footer(text=f"*{await get_prefix_context(self.bot, interaction)}help* for more info")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def botliste(self, interaction: discord.Interaction, member: discord.Member | discord.User) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return

        bot_list = [guild_member for guild_member in interaction.guild.members if guild_member.bot]
        entries = "\n".join(bot_member.mention for bot_member in bot_list) or "Keine Bots gefunden."
        embed = discord.Embed(title=f"Bot Liste (Anzahl: {len(bot_list)})", description=entries)
        embed.set_footer(text=f"*{await get_prefix_context(self.bot, interaction)}help* for more info")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | discord.User) -> None:
        if interaction.guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message("Dieser Befehl funktioniert nur fuer Server-Mitglieder.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Userinfo fuer {member.name}",
            description=f"Dies ist eine Userinfo fuer den User {member.mention}",
            color=0x22A7F0,
        )
        embed.add_field(name="Server beigetreten", value=member.joined_at.strftime("%d/%m/%Y, %H:%M:%S"), inline=True)
        embed.add_field(name="Discord beigetreten", value=member.created_at.strftime("%d/%m/%Y, %H:%M:%S"), inline=True)

        roles = "\n".join(role.mention for role in member.roles if not role.is_default())
        if roles:
            embed.add_field(name="Rollen", value=roles, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="*LEL* for more info")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def serverinfo(self, interaction: discord.Interaction, member: discord.Member | discord.User) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Dieser Befehl funktioniert nur auf einem Server.", ephemeral=True)
            return

        guild = interaction.guild
        embed = discord.Embed(
            title=f"*{guild.name}* \u200b Informationen",
            description=guild.description or "Keine Beschreibung vorhanden.",
            color=discord.Color.dark_blue(),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Sprache", value=guild.preferred_locale, inline=True)
        embed.add_field(name="Besitzer", value=guild.owner.mention if guild.owner else "Unbekannt", inline=True)
        embed.add_field(name="Anzahl Mitglieder", value=str(guild.member_count), inline=True)
        embed.add_field(name="Erstellt am", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Members(bot))
