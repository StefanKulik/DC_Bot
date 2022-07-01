import discord
import asyncio

from random import choice
from threading import Thread
from config.Util import delete_thread
from discord.ui import View, Button
from discord import Member, ButtonStyle, Interaction, Embed, ChannelType
from discord.ext import commands


######################  TTT handling  #######################
# TODO: Benachrichtigung wenn man dran ist
class TTT(View):
    def __init__(self, ctx, player1: Member, player2: Member, active: Member, thread: Thread):
        super().__init__()
        self.ctx = ctx
        self.thread = thread
        self.player1 = player1
        self.player2 = player2
        self.active = active
        self.game = ['-', '-', '-',
                     '-', '-', '-',
                     '-', '-', '-']
        self.winning_condition = [
            [0, 1, 2],
            [3, 4, 5],
            [6, 7, 8],
            [0, 3, 6],
            [1, 4, 7],
            [2, 5, 8],
            [0, 4, 8],
            [2, 4, 6],
        ]

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=0)
    async def b1_callback(self, button, interaction):
        await self.logic(button, interaction, 0)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=0)
    async def b2_callback(self, button, interaction):
        await self.logic(button, interaction, 1)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=0)
    async def b3_callback(self, button, interaction):
        await self.logic(button, interaction, 2)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=1)
    async def b4_callback(self, button, interaction):
        await self.logic(button, interaction, 3)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=1)
    async def b5_callback(self, button, interaction):
        await self.logic(button, interaction, 4)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=1)
    async def b6_callback(self, button, interaction):
        await self.logic(button, interaction, 5)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=2)
    async def b7_callback(self, button, interaction):
        await self.logic(button, interaction, 6)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=2)
    async def b8_callback(self, button, interaction):
        await self.logic(button, interaction, 7)

    @discord.ui.button(label=' ', style=ButtonStyle.grey, row=2)
    async def b9_callback(self, button, interaction):
        await self.logic(button, interaction, 8)

    async def interaction_check(self, interaction):
        if self.active == self.player1 and interaction.user == self.player1:
            return interaction.user == self.player1
        if self.active == self.player2:
            return interaction.user == self.player2

    async def switch_player(self):
        if self.active == self.player1:
            self.active = self.player2
        else:
            self.active = self.player1
        await self.thread.purge(limit=1)
        await self.thread.send(f'{self.active.mention} ist an der Reihe')

    async def logic(self, button: Button, interaction: Interaction, num):
        if self.active == self.player1:
            button.label = 'X'
            button.style = ButtonStyle.primary
            self.game[num] = self.active.name
        else:
            button.label = 'O'
            button.style = ButtonStyle.danger
            self.game[num] = self.active.name
        if await self.check_winner():
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            await self.thread.purge(limit=1)
            await self.thread.send(embed=Embed(title=' ', description=f'{self.active.mention} hat das Spiel gewonnen'))
            await asyncio.sleep(5)
            await self.thread.send(view=RestartTTT(self.ctx, self.player1, self.player2, self.thread))
        elif all(x not in ['-'] for x in self.game):
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            await self.thread.purge(limit=1)
            await self.thread.send(embed=Embed(title=' ', description='Das Spiel ist Unentschieden'))
            await asyncio.sleep(5)
            await self.thread.send(view=RestartTTT(self.ctx, self.player1, self.player2, self.thread))
        else:
            await interaction.response.edit_message(view=self)
            await self.switch_player()

    async def check_winner(self):
        winner = False
        for condition in self.winning_condition:
            if self.game[condition[0]] == self.active.name and \
                    self.game[condition[1]] == self.active.name and \
                    self.game[condition[2]] == self.active.name:
                winner = True
        return winner


class RestartTTT(View):
    def __init__(self, ctx, player1: Member, player2: Member, thread: Thread):
        super().__init__()
        self.ctx = ctx
        self.thread = thread
        self.player1 = player1
        self.player2 = player2
        self.active = choice([player1, player2])

    @discord.ui.button(label='Neustarten', style=ButtonStyle.success, row=0)
    async def restart_callback(self, button, interaction):
        await self.thread.send(f'{self.active.mention} ist an der Reihe')
        await interaction.response.edit_message(
            view=TTT(self.ctx, self.player1, self.player2, self.active, self.thread))

    @discord.ui.button(label='Beenden', style=ButtonStyle.danger, row=0)
    async def end_callback(self, button, interaction):
        await delete_thread(self.ctx, 'ttt', self.player2)

    async def interaction_check(self, interaction):
        return interaction.user == self.player1 or interaction.user == self.player2


class RequestTTT(View):
    def __init__(self, ctx, player2: Member):
        super().__init__()
        self.ctx = ctx
        self.player2 = player2

    @discord.ui.button(label='Annehmen', style=ButtonStyle.success, row=0)
    async def accept_callback(self, button, interaction):
        thread_name = f"ttt-{self.ctx.author.name.lower().replace(' ', '_')}-{self.player2.name.lower().replace(' ', '_')}"
        channel = self.ctx.guild.get_channel(876278253025914911)
        thread = await channel.create_thread(name=thread_name, message=None, type=ChannelType.public_thread,
                                             reason=None)
        await thread.add_user(self.ctx.author)
        await thread.add_user(self.player2)

        active = choice([self.ctx.author, self.player2])
        e = Embed(title=f'Tic Tac Toe', description=f':regional_indicator_x: {self.ctx.author.name} vs. :o2: {self.player2.name}')
        await thread.send(embed=e)
        await thread.send(view=TTT(self.ctx, self.ctx.author, self.player2, active, thread))
        await thread.send(f'{active.mention} ist an der Reihe')

        await self.ctx.channel.purge(limit=4)

    @discord.ui.button(label='Ablehnen', style=ButtonStyle.danger, row=0)
    async def decline_callback(self, button, interaction):
        await self.delete(interaction)

    async def interaction_check(self, interaction):
        return interaction.user == self.player2

    async def delete(self, interaction):
        await self.ctx.channel.purge(limit=3)
        await interaction.response.send_message('Duell wurde abgelehnt!')
        await asyncio.sleep(2)
        await self.ctx.channel.purge(limit=1)


class TicTacToe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='ttt', description='Erstelle ein Thread für dein "TTT" Spiel')
    async def ttt_create(self, ctx, enemy: Member):
        await ctx.channel.purge(limit=1)

        if ctx.channel.id == 876278253025914911:
            await ctx.respond('Duell angefragt', ephemeral=True)
            await ctx.send(enemy.mention)
            e = Embed(title=':crossed_swords: Tic Tac Toe Duell',
                      description=f'{ctx.author.mention} hat dich herausgefordert')
            await ctx.send(embed=e)
            await ctx.send(view=RequestTTT(ctx, enemy))
        else:
            msg = discord.Embed(title="'Tic Tac Toe' bitte nur im vorgesehen Channel spielen. Danke :)",
                                description="[Tic Tac Toe Channel](https://discord.gg/fyGp97eXmU)")
            await ctx.send(embed=msg)


def setup(bot):
    bot.add_cog(TicTacToe(bot))
