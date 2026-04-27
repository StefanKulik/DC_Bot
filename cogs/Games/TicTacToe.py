from random import choice

import discord
from discord import app_commands
from discord.ext import commands


TTT_CHANNEL_ID = 1496504118884434042


class TTT(discord.ui.View):
    WINNING_CONDITIONS = (
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    )

    def __init__(
        self,
        player1: discord.Member,
        player2: discord.Member,
        active: discord.Member,
        thread: discord.Thread,
    ):
        super().__init__(timeout=600)
        self.thread = thread
        self.player1 = player1
        self.player2 = player2
        self.active = active
        self.board: list[int | None] = [None] * 9
        self.message: discord.Message | None = None
        self.status_message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.active.id:
            return True
        if interaction.user.id in {self.player1.id, self.player2.id}:
            await interaction.response.send_message("Du bist gerade nicht am Zug.", ephemeral=True)
            return False
        await interaction.response.send_message("Das ist nicht dein Spiel.", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)

    def get_symbol(self, player_id: int | None) -> str:
        if player_id == self.player1.id:
            return "X"
        if player_id == self.player2.id:
            return "O"
        return " "

    def has_winner(self) -> bool:
        for first, second, third in self.WINNING_CONDITIONS:
            if self.board[first] == self.board[second] == self.board[third] == self.active.id:
                return True
        return False

    def is_tie(self) -> bool:
        return all(slot is not None for slot in self.board)

    async def switch_player(self) -> None:
        self.active = self.player2 if self.active.id == self.player1.id else self.player1
        if self.status_message is not None:
            await self.status_message.edit(content=f"{self.active.mention} ist an der Reihe")

    async def process_move(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
        index: int,
    ) -> None:
        if self.board[index] is not None:
            await interaction.response.send_message("Dieses Feld ist bereits belegt.", ephemeral=True)
            return

        self.board[index] = self.active.id
        button.label = self.get_symbol(self.active.id)
        button.style = discord.ButtonStyle.primary if self.active.id == self.player1.id else discord.ButtonStyle.danger
        button.disabled = True

        if self.has_winner():
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            if self.status_message is not None:
                await self.status_message.edit(content=f"{self.active.mention} hat das Spiel gewonnen!")
            await self.thread.send(view=RestartTTT(self.player1, self.player2, self.thread))
            return

        if self.is_tie():
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            if self.status_message is not None:
                await self.status_message.edit(content="Das Spiel ist unentschieden.")
            await self.thread.send(view=RestartTTT(self.player1, self.player2, self.thread))
            return

        await interaction.response.edit_message(view=self)
        await self.switch_player()

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=0)
    async def b1_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 0)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=0)
    async def b2_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 1)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=0)
    async def b3_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 2)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=1)
    async def b4_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 3)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=1)
    async def b5_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 4)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=1)
    async def b6_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 5)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=2)
    async def b7_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 6)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=2)
    async def b8_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 7)

    @discord.ui.button(label="\u200b", style=discord.ButtonStyle.secondary, row=2)
    async def b9_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.process_move(interaction, button, 8)


class RestartTTT(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member, thread: discord.Thread):
        super().__init__(timeout=300)
        self.thread = thread
        self.player1 = player1
        self.player2 = player2

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id in {self.player1.id, self.player2.id}:
            return True
        await interaction.response.send_message("Das ist nicht dein Spiel.", ephemeral=True)
        return False

    @discord.ui.button(label="Neustarten", style=discord.ButtonStyle.success)
    async def restart_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        active = choice([self.player1, self.player2])
        game_view = TTT(self.player1, self.player2, active, self.thread)
        embed = discord.Embed(
            title="Tic Tac Toe",
            description=f":regional_indicator_x: {self.player1.name} vs. :o2: {self.player2.name}",
        )
        board_message = await self.thread.send(embed=embed, view=game_view)
        status_message = await self.thread.send(f"{active.mention} ist an der Reihe")
        game_view.message = board_message
        game_view.status_message = status_message
        self.stop()
        await interaction.response.edit_message(content="Neues Spiel gestartet.", view=None)

    @discord.ui.button(label="Beenden", style=discord.ButtonStyle.danger)
    async def end_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(content="Spiel beendet.", view=None)
        await self.thread.delete()


class RequestTTT(discord.ui.View):
    def __init__(
        self,
        requester: discord.Member,
        opponent: discord.Member,
        channel: discord.TextChannel,
    ):
        super().__init__(timeout=300)
        self.requester = requester
        self.opponent = opponent
        self.channel = channel

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.opponent.id:
            return True
        await interaction.response.send_message("Nur die herausgeforderte Person kann hier reagieren.", ephemeral=True)
        return False

    @discord.ui.button(label="Annehmen", style=discord.ButtonStyle.success)
    async def accept_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        thread_name = f"ttt-{self.requester.name.lower().replace(' ', '_')}-{self.opponent.name.lower().replace(' ', '_')}"
        starter_message = await self.channel.send(
            f"{self.requester.mention} und {self.opponent.mention} starten eine Runde Tic Tac Toe."
        )
        thread = await starter_message.create_thread(name=thread_name, auto_archive_duration=60)
        await thread.send("Test")
        active = choice([self.requester, self.opponent])
        game_view = TTT(self.requester, self.opponent, active, thread)
        embed = discord.Embed(
            title="Tic Tac Toe",
            description=f":regional_indicator_x: {self.requester.name} vs. :o2: {self.opponent.name}",
        )
        board_message = await thread.send(embed=embed, view=game_view)
        #board_message = await thread.send(embed=embed)
        status_message = await thread.send(f"{active.mention} ist an der Reihe")
        game_view.message = board_message
        game_view.status_message = status_message
        self.stop()
        await interaction.response.edit_message(content="Duell angenommen.", embed=None, view=None)

    @discord.ui.button(label="Ablehnen", style=discord.ButtonStyle.danger)
    async def decline_callback(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.response.edit_message(content="Duell wurde abgelehnt!", embed=None, view=None)


class TicTacToe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ttt", description='Erstelle ein Thread fuer dein "TTT" Spiel')
    @app_commands.guild_only()
    @app_commands.describe(enemy="Gegner fuer das Duell")
    async def ttt_create(self, interaction: discord.Interaction, enemy: discord.Member) -> None:
        if interaction.guild is None or not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("Dieser Befehl funktioniert nur in einem Server-Textkanal.", ephemeral=True)
            return

        if interaction.user.id == enemy.id:
            await interaction.response.send_message("Du kannst dich nicht selbst herausfordern.", ephemeral=True)
            return

        if interaction.channel.id != TTT_CHANNEL_ID:
            embed = discord.Embed(
                title="'Tic Tac Toe' bitte nur im vorgesehenen Channel spielen.",
                description="[Tic Tac Toe Channel](https://discord.gg/zhwQjAJvCn)",
                color=discord.Color.red(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title=":crossed_swords: Tic Tac Toe Duell",
            description=f"{interaction.user.mention} hat dich herausgefordert",
        )
        view = RequestTTT(interaction.user, enemy, interaction.channel)
        await interaction.response.send_message(content=enemy.mention, embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TicTacToe(bot))
