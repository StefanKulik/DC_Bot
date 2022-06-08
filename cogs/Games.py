import asyncio
from random import choice

import discord
from discord import ChannelType, ButtonStyle, Embed
from discord.ext import commands
from discord.ui import Button, View, button


class RPS(View):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx
        self.value = None

    @button(label='Schere', style=ButtonStyle.red, custom_id='schere')
    async def schere_callback(self, button, interaction):
        self.value = 'Schere'
        self.stop()

    @button(label='Stein', style=ButtonStyle.primary)
    async def stein_callback(self, button, interaction):
        self.value = 'Stein'
        self.stop()

    @button(label='Papier', style=ButtonStyle.success)
    async def papier_callback(self, button, interaction):
        self.value = 'Papier'
        self.stop()

    @button(label='Ende', style=ButtonStyle.grey)
    async def ende_callback(self, button, interaction):
        self.value = 'Ende'
        self.stop()

    async def interaction_check(self, interaction) -> bool:
        return interaction.user == self.ctx.author


async def rock_paper_scissors(self, ctx):
    await ctx.channel.purge(limit=1)
    rps = ["Stein", "Papier", "Schere"]
    comp = ''
    wins = 0
    loses = 0
    ties = 0
    tos = 0
    game = True

    yet = Embed(title=f"{ctx.author.name}`s Schere Stein Papier!",
                description=">Status: Du hast noch keinen Knopf gedrückt!", color=0xFFEA00)
    win = Embed(title=f"{ctx.author.name}, Sieg!",
                description=f">Status: **DU hast gewonnen!** Ich habe ***{comp}*** gewählt",
                color=0x00FF00)
    out = Embed(title=f"{ctx.author.name}, Du hast nicht rechtzeitig gedrückt!",
                description=">Status: **Zeitüberschreitung**",
                color=discord.Color.red())
    loss = Embed(title=f"{ctx.author.name}, Verloren!",
                 description=f">Status: **Du hast verloren** Ich habe ***{comp}*** gewählt",
                 color=discord.Color.red())
    tie = Embed(title=f"{ctx.author.name}, Unentschieden!",
                description=f">Status: **Unentschieden!** Wir beide haben ***{comp}*** gewählt",
                color=0x00FF00)
    end = Embed(title="Danke fürs Spielen von 'Schere Stein Papier'!",
                description=f"Siege: {wins}\n Niederlagen: {loses}\n Unentschieden: {ties}\n",
                color=0xFFEA00)

    while game:
        view = RPS(ctx)

        m = await ctx.send(
            embed=yet,
            view=view
        )
        await view.wait()

        player = view.value
        comp = choice(rps)

        if player == comp:
            await m.edit(embed=tie, view=view)
            ties += 1
            await asyncio.sleep(2)
            await ctx.channel.purge(1)

        if (player == "Stein" and comp == "Papier") or (player == "Schere" and comp == "Stein") or (
                            player == "Papier" and comp == "Schere"):
            await m.edit(embed=loss, view=view)
            loses += 1
            await asyncio.sleep(2)
            await ctx.channel.purge(1)

        if (player == "Stein" and comp == "Schere") or (player == "Schere" and comp == "Papier") or (
                            player == "Papier" and comp == "Stein"):
            await m.edit(embed=win, view=view)
            wins += 1
            await asyncio.sleep(2)
            await ctx.channel.purge(1)

        if player == 'Ende':
            game = False
            await m.edit(embed=end, view=None, delete_after=10)
    return


class Games(commands.Cog, description="Games Befehle"):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ssp", description="Erstelle ein Raum für dein 'Schere Stein Papier' Spiel")
    async def ssp_create(self, ctx):
        await ctx.channel.purge(limit=1)
        if ctx.channel.id == 876278221878992916:
            role_channel_name = f"ssp-{ctx.author.name.lower().replace(' ', '_')}"

            channel = ctx.guild.get_channel(876278221878992916)

            await channel.create_thread(name=role_channel_name, message=None, type=ChannelType.public_thread,
                                        reason=None)
        else:
            msg = discord.Embed(title="'Schere Stein Papier' bitte nur im vorgesehem Channel spielen. Danke :)",
                                description="[Schere Stein Papier Channel](https://discord.gg/rkfGskKRxF)")
            await ctx.send(embed=msg)

    @commands.command()
    async def start(self, ctx):
        if "ttt" in ctx.channel.name:
            # await tic_tac_toe(ctx)
            pass
        elif "ssp" in ctx.channel.name:
            # await ctx.send("ssp")
            await rock_paper_scissors(self, ctx)
        else:
            await ctx.send("Konnte kein Spiel starten")

    @commands.command()
    async def end(self, ctx):
        threads = ctx.guild.get_channel(876278221878992916).threads
        for thread in threads:
            if thread.name == 'ssp-' + ctx.author.name.lower().replace(' ', '_'):
                await thread.delete()


############################################################
def setup(bot):
    bot.add_cog(Games(bot))
