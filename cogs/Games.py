import asyncio
from random import choice

import discord
from discord import ChannelType, ButtonStyle, Embed, Interaction, Member, option, Message, Thread
from discord.ext import commands
from discord.ui import View, Button


######################  RPS handling  #######################
class RPS(View):
    def __init__(self, ctx, m, thread):
        super().__init__()
        self.ctx = ctx
        self.message = m
        self.thread = thread
        self.value = None
        self.rps = ["Stein", "Papier", "Schere"]
        self.wins = 0
        self.loses = 0
        self.ties = 0
        self.game = True

    @discord.ui.button(label='Schere', style=ButtonStyle.red, custom_id='schere')
    async def schere_callback(self, button, interaction):
        self.value = 'Schere'
        await self.logic(interaction)

    @discord.ui.button(label='Stein', style=ButtonStyle.primary)
    async def stein_callback(self, button, interaction):
        self.value = 'Stein'
        await self.logic(interaction)

    @discord.ui.button(label='Papier', style=ButtonStyle.success)
    async def papier_callback(self, button, interaction):
        self.value = 'Papier'
        await self.logic(interaction)

    @discord.ui.button(label='Ende', style=ButtonStyle.grey)
    async def ende_callback(self, button, interaction):
        self.value = 'Ende'
        await self.logic(interaction)

    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author

    async def logic(self, interaction: Interaction):
        comp = choice(self.rps)
        player = self.value

        win = Embed(title=f"{self.ctx.author.name}, Sieg!",
                    description=f">Status: **DU hast gewonnen!** Ich habe ***{comp}*** gewählt",
                    color=0x00FF00)
        loss = Embed(title=f"{self.ctx.author.name}, Verloren!",
                     description=f">Status: **Du hast verloren** Ich habe ***{comp}*** gewählt",
                     color=discord.Color.red())
        tie = Embed(title=f"{self.ctx.author.name}, Unentschieden!",
                    description=f">Status: **Unentschieden!** Wir beide haben ***{comp}*** gewählt",
                    color=0xFFEA00)
        end = Embed(title="Danke fürs Spielen von 'Schere Stein Papier'!",
                    description=f"Siege: {self.wins}\n Niederlagen: {self.loses}\n Unentschieden: {self.ties}\n",
                    color=0xFFEA00)

        if player == comp:
            await self.message.edit(embed=tie)
            self.ties = self.ties + 1
            await interaction.response.edit_message(view=self)
            await asyncio.sleep(2)

        if (player == "Stein" and comp == "Papier") or (player == "Schere" and comp == "Stein") or (
                player == "Papier" and comp == "Schere"):
            await self.message.edit(embed=loss)
            self.loses = self.loses + 1
            await interaction.response.edit_message(view=self)
            await asyncio.sleep(2)

        if (player == "Stein" and comp == "Schere") or (player == "Schere" and comp == "Papier") or (
                player == "Papier" and comp == "Stein"):
            await self.message.edit(embed=win)
            self.wins = self.wins + 1
            await interaction.response.edit_message(view=self)
            await asyncio.sleep(2)

        if player == 'Ende':
            self.game = False
            await interaction.response.edit_message(view=self)
            await self.message.edit(embed=end)
            await self.thread.purge(limit=1)
            await self.thread.send(view=RestartRPS(self.ctx, self.message, self.thread))


class RestartRPS(View):
    def __init__(self, ctx, m: Message, thread: Thread):
        super().__init__()
        self.ctx = ctx
        self.thread = thread
        self.message = m

    @discord.ui.button(label='Neustarten', style=ButtonStyle.success, row=0)
    async def restart_callback(self, button, interaction):
        e = Embed(title=f"{self.ctx.author.name}`s Schere Stein Papier!",
                  description=">Status: Du hast noch keinen Knopf gedrückt!", color=0xFFEA00)
        await self.message.edit(embed=e)
        await interaction.response.edit_message(
            view=RPS(self.ctx, self.message, self.thread))

    @discord.ui.button(label='Beenden', style=ButtonStyle.danger, row=0)
    async def end_callback(self, button, interaction):
        await delete_thread(self.ctx, 'rps')

    async def interaction_check(self, interaction):
        return interaction.user == self.ctx.author


######################  TTT handling  #######################
# TODO: Benachrichtigung wenn man dran ist
class TTT(View):
    def __init__(self, ctx, player1: Member, player2: Member, active: Member, m: Message, thread: Thread):
        super().__init__()
        self.ctx = ctx
        self.thread = thread
        self.player1 = player1
        self.player2 = player2
        self.active = active
        self.message = m
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
        e = Embed(title='Tic Tac Toe', description=f'{self.active.mention} ist an der Reihe')
        await self.message.edit(embed=e)

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
            await asyncio.sleep(1)
            if all(x not in ['-'] for x in self.game):
                await self.message.edit(embed=Embed(title='Tic Tac Toe',
                                                    description='Das Spiel ist Unentschieden'))
            else:
                await self.message.edit(embed=Embed(title='Tic Tac Toe',
                                                    description=f'{self.active.mention} hat das Spiel gewonnen'))
            await asyncio.sleep(5)
            await self.thread.purge(limit=1)
            await self.thread.send(view=RestartTTT(self.ctx, self.player1, self.player2, self.message, self.thread))
        else:
            await interaction.response.edit_message(view=self)
            await self.switch_player()

    async def check_winner(self):
        winner = False
        if all(x not in ['-'] for x in self.game):
            winner = True
        else:
            for condition in self.winning_condition:
                if self.game[condition[0]] == self.active.name and \
                        self.game[condition[1]] == self.active.name and \
                        self.game[condition[2]] == self.active.name:
                    winner = True
        return winner


class RestartTTT(View):
    def __init__(self, ctx, player1: Member, player2: Member, m: Message, thread: Thread):
        super().__init__()
        self.ctx = ctx
        self.thread = thread
        self.player1 = player1
        self.player2 = player2
        self.active = choice([player1, player2])
        self.message = m

    @discord.ui.button(label='Neustarten', style=ButtonStyle.success, row=0)
    async def restart_callback(self, button, interaction):
        e = Embed(title='Tic Tac Toe', description=f'{self.active.mention} ist an der Reihe')
        await self.message.edit(embed=e)
        await interaction.response.edit_message(
            view=TTT(self.ctx, self.player1, self.player2, self.active, self.message, self.thread))

    @discord.ui.button(label='Beenden', style=ButtonStyle.danger, row=0)
    async def end_callback(self, button, interaction):
        await delete_thread(self.ctx, 'ttt', self.player2)

    async def interaction_check(self, interaction):
        if self.active == self.player1 and interaction.user == self.player1:
            return interaction.user == self.player1
        if self.active == self.player2:
            return interaction.user == self.player2


class Request(View):
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
        e = Embed(title='Tic Tac Toe', description=f'{active.mention} ist an der Reihe')
        m = await thread.send(embed=e)
        await thread.send(view=TTT(self.ctx, self.ctx.author, self.player2, active, m, thread))
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


########################  Function  #########################
async def delete_thread(ctx, mode: str, member: Member = None):
    if mode == 'ttt':
        threads = ctx.guild.get_channel(876278253025914911).threads
        for thread in threads:
            if thread.name == f"ttt-{ctx.author.name.lower().replace(' ', '_')}-{member.name.lower().replace(' ', '_')}":
                await thread.delete()
    elif mode == 'rps':
        threads = ctx.guild.get_channel(876278221878992916).threads
        for thread in threads:
            if thread.name == 'ssp-' + ctx.author.name.lower().replace(' ', '_'):
                await thread.delete()


########################### Klasse ##########################
class Games(commands.Cog, description="Games Befehle"):

    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='ssp', description='Erstelle ein Raum für dein "Schere Stein Papier" Spiel')
    async def ssp_create(self, ctx):
        await ctx.channel.purge(limit=1)
        if ctx.channel.id == 876278221878992916:
            await ctx.respond('Thread erstellt', ephemeral=True)
            thread_name = f"ssp-{ctx.author.name.lower().replace(' ', '_')}"
            channel = ctx.guild.get_channel(876278221878992916)
            thread = await channel.create_thread(name=thread_name, message=None, type=ChannelType.public_thread,
                                                 reason=None)
            await thread.add_user(ctx.author)

            e = Embed(title=f"{ctx.author.name}`s Schere Stein Papier!",
                      description=">Status: Du hast noch keinen Knopf gedrückt!", color=0xFFEA00)
            m = await thread.send(embed=e)
            await m.pin()
            await thread.purge(limit=1)
            await thread.send(view=RPS(ctx, m, thread))

        else:
            msg = Embed(title="'Schere Stein Papier' bitte nur im vorgesehem Channel spielen. Danke :)",
                        description="[Schere Stein Papier Channel](https://discord.gg/rkfGskKRxF)")
            await ctx.respond(embed=msg, ephemeral=True)

    @commands.slash_command(name='ttt', description='Erstelle ein Thread für dein "TTT" SPiel')
    async def ttt_create(self, ctx, enemy: Member):
        await ctx.channel.purge(limit=1)

        if ctx.channel.id == 876278253025914911:
            await ctx.respond('Duell angefragt', ephemeral=True)
            await ctx.send(enemy.mention)
            e = Embed(title=':crossed_swords: Tic Tac Toe Duell',
                      description=f'{ctx.author.mention} hat dich herausgefordert')
            await ctx.send(embed=e)
            await ctx.send(view=Request(ctx, enemy))
        else:
            msg = discord.Embed(title="'Tic Tac Toe' bitte nur im vorgesehem Channel spielen. Danke :)",
                                description="[Tic Tac Toe Channel](https://discord.gg/fyGp97eXmU)")
            await ctx.send(embed=msg)


#############################################################
def setup(bot):
    bot.add_cog(Games(bot))
