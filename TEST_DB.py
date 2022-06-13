#
# @bot.command(aliases=['ggc'])
# @commands.has_permissions(administrator=True)
# async def getglobalchat(ctx):
#     print(ctx.guild.name)
#     # globalchats = await bot.db.fetch('SELECT * FROM globalchat')
#
#
# @bot.command(aliases=['agc'])
# @commands.has_permissions(administrator=True)
# async def addglobalchat(ctx):
#     invite = (await ctx.channel.create_invite()).url
#     await bot.db.execute(f'INSERT INTO globalchat(guild_id, channel_id, invite) '
#                          f'VALUES($1, $2, $3)', ctx.guild.id, ctx.channel.id, invite)
#
#
# @bot.command(aliases=['rgc'])
# @commands.has_permissions(administrator=True)
# async def removeglobalchat(ctx):
#     await bot.db.execute('DELETE FROM globalchat WHERE channel_id = $1', ctx.channel.id)

