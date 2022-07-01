import asyncio
from random import choice

import discord
from discord import Embed, ChannelType, ButtonStyle, Message, Thread, Interaction
from discord.ext import commands
from discord.ui import View

from config.Util import delete_thread


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


class RockPaperScissors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='rps', description='Erstelle ein Raum für dein "Schere Stein Papier" Spiel')
    async def rps_create(self, ctx):
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
            msg = Embed(title="'Schere Stein Papier' bitte nur im vorgesehen Channel spielen. Danke :)",
                        description="[Schere Stein Papier Channel](https://discord.gg/rkfGskKRxF)")
            await ctx.respond(embed=msg, ephemeral=True)


def setup(bot):
    bot.add_cog(RockPaperScissors(bot))
