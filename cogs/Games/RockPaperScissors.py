from random import choice

import discord
from discord import app_commands
from discord.ext import commands


RPS_CHANNEL_ID = 1496504095379427479


class RPS(discord.ui.View):
    MOVES = ("Stein", "Papier", "Schere")
    WINNING_MOVES = {
        ("Stein", "Schere"),
        ("Schere", "Papier"),
        ("Papier", "Stein"),
    }

    def __init__(self, author_id: int, author_name: str, thread: discord.Thread):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.author_name = author_name
        self.thread = thread
        self.message: discord.Message | None = None
        self.wins = 0
        self.losses = 0
        self.ties = 0

    def build_embed(self, status: str, color: discord.Color) -> discord.Embed:
        return discord.Embed(
            title=f"{self.author_name}s Schere Stein Papier!",
            description=status,
            color=color,
        )

    def build_initial_embed(self) -> discord.Embed:
        return self.build_embed("> Status: Du hast noch keinen Knopf gedrueckt!", discord.Color.gold())

    def build_summary_embed(self) -> discord.Embed:
        return discord.Embed(
            title="Danke fuers Spielen von 'Schere Stein Papier'!",
            description=(
                f"Siege: {self.wins}\n"
                f"Niederlagen: {self.losses}\n"
                f"Unentschieden: {self.ties}"
            ),
            color=discord.Color.gold(),
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("Das ist nicht dein Spiel.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)

    async def play_round(self, interaction: discord.Interaction, player_move: str) -> None:
        computer_move = choice(self.MOVES)

        if player_move == computer_move:
            self.ties += 1
            embed = self.build_embed(
                f"> Status: **Unentschieden!** Wir beide haben **{computer_move}** gewaehlt.",
                discord.Color.gold(),
            )
        elif (player_move, computer_move) in self.WINNING_MOVES:
            self.wins += 1
            embed = self.build_embed(
                f"> Status: **Du hast gewonnen!** Ich habe **{computer_move}** gewaehlt.",
                discord.Color.green(),
            )
        else:
            self.losses += 1
            embed = self.build_embed(
                f"> Status: **Du hast verloren!** Ich habe **{computer_move}** gewaehlt.",
                discord.Color.red(),
            )

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Schere", style=discord.ButtonStyle.danger)
    async def schere_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.play_round(interaction, "Schere")

    @discord.ui.button(label="Stein", style=discord.ButtonStyle.primary)
    async def stein_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.play_round(interaction, "Stein")

    @discord.ui.button(label="Papier", style=discord.ButtonStyle.success)
    async def papier_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.play_round(interaction, "Papier")

    @discord.ui.button(label="Ende", style=discord.ButtonStyle.secondary)
    async def ende_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        restart_view = RestartRPS(
            author_id=self.author_id,
            author_name=self.author_name,
            thread=self.thread,
        )
        restart_view.message = self.message
        restart_view.stats = (self.wins, self.losses, self.ties)
        self.stop()
        await interaction.response.edit_message(embed=self.build_summary_embed(), view=restart_view)


class RestartRPS(discord.ui.View):
    def __init__(self, author_id: int, author_name: str, thread: discord.Thread):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.author_name = author_name
        self.thread = thread
        self.message: discord.Message | None = None
        self.stats = (0, 0, 0)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.author_id:
            return True
        await interaction.response.send_message("Das ist nicht dein Spiel.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)

    @discord.ui.button(label="Neustarten", style=discord.ButtonStyle.success)
    async def restart_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        new_view = RPS(self.author_id, self.author_name, self.thread)
        new_view.message = interaction.message
        await interaction.response.edit_message(embed=new_view.build_initial_embed(), view=new_view)

    @discord.ui.button(label="Beenden", style=discord.ButtonStyle.danger)
    async def end_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(view=None)
        await self.thread.delete()


class RockPaperScissors(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="rps", description='Erstelle ein Thread fuer dein "Schere Stein Papier" Spiel')
    @app_commands.guild_only()
    async def rps_create(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Dieser Befehl funktioniert nur in einem Server-Textkanal.", ephemeral=True)
            return

        if interaction.channel.id != RPS_CHANNEL_ID:
            embed = discord.Embed(
                title="'Schere Stein Papier' bitte nur im vorgesehenen Channel spielen.",
                description="[Schere Stein Papier Channel](https://discord.gg/Rr3zcGU9JC)",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        thread_name = f"ssp-{interaction.user.display_name.lower().replace(' ', '_')}"
        starter_message = await interaction.channel.send(f"{interaction.user.mention} startet eine Runde Schere Stein Papier.")
        thread = await starter_message.create_thread(name=thread_name, auto_archive_duration=60)

        view = RPS(interaction.user.id, interaction.user.display_name, thread)
        game_message = await thread.send(embed=view.build_initial_embed(), view=view)
        view.message = game_message
        await game_message.pin()

        await interaction.followup.send(f"Thread erstellt: {thread.mention}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RockPaperScissors(bot))
