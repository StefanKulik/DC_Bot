from discord import Embed
from discord.ext import commands

from config.Util import globalchat_exists, send_embed, is_globalchat


########################### Klasse ##########################
class Globalchat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # @command(aliases=['agc'])
    # @commands.has_permissions(administrator=True)
    # async def addglobalchat(self, ctx):
    #     invite = (await ctx.channel.create_invite()).url
    #     await self.bot.db.execute('INSERT INTO globalchat(guild_id, channel_id, invite, name) '
    #                               'VALUES($1, $2, $3, $4)', ctx.guild.id, ctx.channel.id, invite, ctx.guild.name)

    @commands.slash_command(name='addglobal')
    @commands.has_permissions(administrator=True)
    async def addglobal(self, ctx):
        if not await globalchat_exists(self, ctx.guild.id):
            invite = (await ctx.channel.create_invite()).url
            await self.bot.db.execute('INSERT INTO globalchat(guild_id, channel_id, invite, name) '
                                      'VALUES($1, $2, $3, $4)', ctx.guild.id, ctx.channel.id, invite, ctx.guild.name)

            embed = Embed(title=f"**Willkommen im GlobalChat von '{ctx.guild.name}'™**",
                          description="Dein Server ist einsatzbereit!"
                                      " Ab jetzt werden alle Nachrichten in diesem Channel direkt an alle"
                                      " anderen Server weitergeleitet!",
                          color=0x2ecc71)
            embed.set_footer(text='Bitte beachte, dass im GlobalChat stets ein Slowmode von mindestens 5 Sekunden'
                                  ' gesetzt sein sollte.')
            # 🌍
            # name_new = f"🌍-{str(ctx.channel)}"
            # await ctx.channel.edit(name=f"{name_new}")
        else:
            invite = await self.bot.db.fetch('SELECT invite FROM globalchat WHERE guild_id = $1', ctx.guild.id)
            embed = Embed(description="Du hast bereits einen GlobalChat auf deinem Server.\r\n"
                                      "Bitte beachte, dass jeder Server nur einen GlobalChat besitzen kann.\r\n"
                                      f"[Klick hier]({invite[0]['invite']})",
                          color=0x2ecc71)
        await send_embed(ctx, embed)

    @commands.slash_command(name='removeglobal')
    @commands.has_permissions(administrator=True)
    async def removeglobal(self, ctx):
        if not await globalchat_exists(self, ctx.guild.id):
            embed = Embed(description="Du hast noch keinen GlobalChat auf deinem Server.\r\n"
                                              "Füge einen mit `/addGlobal`, in einem frischen Channel, hinzu.",
                                  color=0x2ecc71)
        else:
            if await is_globalchat(self.bot, ctx.guild.id, ctx.channel.id):
                await self.bot.db.execute('DELETE FROM globalchat WHERE channel_id = $1', ctx.channel.id)

                embed = Embed(title="**Auf Wiedersehen!**",
                                      description="Der GlobalChat wurde entfernt. Du kannst ihn jederzeit mit"
                                                  " `/addGlobal` neu hinzufügen",
                                      color=0x2ecc71)

                # name_new = str(ctx.channel).replace('🌍-', '\u200b')
                # await ctx.channel.edit(name=f"{name_new}")
            else:
                invite = await self.bot.db.fetch('SELECT invite FROM globalchat WHERE guild_id = $1', ctx.guild.id)
                embed = Embed(description="Du befindest dich nicht in deinem GlobalChat.\r\n"
                                                  f"[Klick hier]({invite[0]['invite']})",
                                      color=0x2ecc71)
        await send_embed(ctx, embed)


#############################################################
def setup(bot):
    bot.add_cog(Globalchat(bot))
