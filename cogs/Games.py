import asyncio
from random import choice

import discord
from discord import ChannelType
from discord.ext import commands
from discord.types.components import ButtonStyle
from discord.ui import Button


async def rock_paper_scissors(self, ctx):
    role_channel_name = f"ssp-{ctx.author.name.lower().replace(' ', '_')}"
    temp_role = discord.utils.get(ctx.guild.roles, name=role_channel_name)
    channel_id = discord.utils.get(ctx.guild.channels, name=role_channel_name).id

    if ctx.channel.id == channel_id:
        wins = 0
        loses = 0
        ties = 0
        tos = 0
        game = True
        while game:
            await ctx.channel.purge(limit=1)
            rps = ["Stein", "Papier", "Schere"]
            comp = choice(rps)
            yet = discord.Embed(title=f"{ctx.author.name}`s Schere Stein Papier!",
                                description=">Status: Du hast noch keinen Knopf gedrückt!", color=0xFFEA00)
            win = discord.Embed(title=f"{ctx.author.name}, Sieg!",
                                description=f">Status: **DU hast gewonnen!** Ich habe ***{comp}*** gewählt",
                                color=0x00FF00)
            out = discord.Embed(title=f"{ctx.author.name}, Du hast nicht rechtzeitig gedrückt!",
                                description=">Status: **Zeitüberschreitung**",
                                color=discord.Color.red())
            lost = discord.Embed(title=f"{ctx.author.name}, Verloren!",
                                 description=f">Status: **Du hast verloren** Ich habe ***{comp}*** gewählt",
                                 color=discord.Color.red())
            tie = discord.Embed(title=f"{ctx.author.name}, Unentschieden!",
                                description=f">Status: **Unentschieden!** Wir beide haben ***{comp}*** gewählt",
                                color=0x00FF00)
            end = discord.Embed(title="Danke fürs Spielen von 'Schere Stein Papier'!",
                                description=f"Siege: {wins}\n Niederlagen: {loses}\n Unentschieden: {ties}\n TOs: {tos}",
                                color=0xFFEA00)

            but = [
                [Button(style=1, label="Stein"),
                 Button(style=3, label="Papier"),
                 Button(style=ButtonStyle.red, label="Schere")],
                [Button(style=ButtonStyle.grey, label="Ende")]
            ]

            m = await ctx.send(
                embed=yet,
                components=but
            )

            def check(res):
                return ctx.author == res.user and res.channel == ctx.channel

            try:
                res = await self.bot.wait_for("button_click", check=check)
                player = res.component.label

                if player == comp:
                    await m.edit(embed=tie, components=[])
                    ties += 1
                    await asyncio.sleep(2)

                if (player == "Stein" and comp == "Papier") or (player == "Schere" and comp == "Stein") or (
                        player == "Papier" and comp == "Schere"):
                    await m.edit(embed=lost, components=[])
                    loses += 1
                    await asyncio.sleep(2)

                if player == "Stein" and comp == "Schere" or (player == "Schere" and comp == "Papier") or (
                        player == "Papier" and comp == "Stein"):
                    await m.edit(embed=win, components=[])
                    wins += 1
                    await asyncio.sleep(2)

                if player == "Ende":
                    game = False
                    await m.edit(embed=end, components=[], delete_after=10)

            except TimeoutError as e:
                await asyncio.sleep(2)
                await m.edit(embed=out, components=[])
                tos += 1
        await asyncio.sleep(10)
        if ctx.author.id == 183185835477172226 or 695183644968615988:
            await ctx.send("fertig")
        else:
            await temp_role.delete()
            await ctx.channel.delete()
        return
    msg = discord.Embed(title="'Schere Stein Papier' bitte nur im vorgesehem Channel spielen. Danke :)")
    await ctx.send(embed=msg)


class Games(commands.Cog, description="Games Befehle"):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ssp", description="Erstelle ein Raum für dein 'Schere Stein Papier' Spiel")
    async def ssp_create(self, ctx):
        await ctx.channel.purge(limit=1)
        if ctx.channel.id == 876278221878992916:
            role_channel_name = f"ssp-{ctx.author.name.lower().replace(' ', '_')}"

            channel = ctx.guild.get_channel(876278221878992916)

            await channel.create_thread(name=role_channel_name, message=None, type=ChannelType.public_thread, reason=None)
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
            await ctx.send("ssp")
            # await rock_paper_scissors(self, ctx)
        else:
            await ctx.send("Konnte kein Spiel starten")

    @commands.command()
    async def end(self, ctx):
        threads = ctx.guild.get_channel(876278221878992916).threads
        for thread in threads:
            if thread.name == 'ssp-'+ctx.author.name.lower().replace(' ', '_'):
                await thread.delete()


############################################################
def setup(bot):
    bot.add_cog(Games(bot))
