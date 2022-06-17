import io
import pathlib

from discord import Message, Member, option, Embed, Color, File
from discord.ext import commands
from discord.utils import get
from PIL import Image, ImageDraw, ImageFont


####################### welcome card #######################
blank_card = pathlib.Path("config/img/level_card.jpg")
background_image = Image.open(blank_card)
background_image = background_image.convert('RGBA')


async def draw_card_level(channel, member: Member):
    avatar_size = 158

    image = background_image.copy()
    image_width, image_height = image.size

    margin_left = 24
    margin_top = 36
    margin_right = image_width - 24
    margin_bottom = image_height - 36

    rect_width = margin_right - margin_left
    rect_height = margin_bottom - margin_top

    draw = ImageDraw.Draw(image)

    text = f'{member} Level X'
    avatar_asset = member.avatar

    buffer_avatar = io.BytesIO(await avatar_asset.read())

    avatar_image = Image.open(buffer_avatar)

    avatar_image = avatar_image.resize((avatar_size, avatar_size))

    circle_image = Image.new('L', (avatar_size, avatar_size))
    circle_draw = ImageDraw.Draw(circle_image)
    circle_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)

    avatar_start_x = 42
    # avatar_start_x = (rect_width // 2) + margin_left - (avatar_size // 2)
    avatar_start_y = 62
    image.paste(avatar_image, (avatar_start_x, avatar_start_y), circle_image)

    font = ImageFont.truetype('config/arial.ttf', 40)  # for heroku

    text_width, text_height = draw.textsize(text, font=font)
    text_start_x = (rect_width // 2) + margin_left - (text_width // 2)
    text_start_y = rect_height - 85

    # draw.text((text_start_x, text_start_y), text, fill=(255, 255, 255, 255), font=font)

    buffer_output = io.BytesIO()

    image.save(buffer_output, format='PNG')

    buffer_output.seek(0)

    await channel.send(file=File(buffer_output, f'level-card.png'))


#############################################################
class Level(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener('on_message')
    async def on_message_admin(self, message: Message):
        if not message.author.bot:
            await self.update_data(message)
            await self.add_experience(message, 5)
            await self.level_up(message)

    async def update_data(self, message):
        if len(await self.bot.db.fetch('SELECT member_id FROM level '
                                       'WHERE member_id = $1 AND guild_id = $2',
                                       message.author.id, message.guild.id)
               ) == 0:
            await self.bot.db.execute('INSERT INTO level(guild_id, member_id, level, level_exp) '
                                      'VALUES($1, $2, $3, $4)', message.guild.id, message.author.id, 1, 0)

    async def add_experience(self, message, exp):
        await self.bot.db.execute('UPDATE level SET level_exp = level_exp + $1 '
                                  'WHERE member_id = $2 AND guild_id = $3', exp, message.author.id, message.guild.id)

    async def level_up(self, message):
        stats = await self.bot.db.fetch('SELECT level, level_exp FROM level WHERE member_id = $1 AND guild_id = $2',
                                        message.author.id, message.guild.id)
        exp = stats[0]['level_exp']
        lvl_start = stats[0]['level']
        lvl_end = int(exp ** (1 / 4))
        exp_new = exp - (lvl_start + 1) ** 4
        if lvl_start < lvl_end:
            c = get(message.guild.channels, id=877680622284455948)
            e = Embed(title='', description=f'{message.author.mention} has leveled up to level {lvl_end}')
            await c.send(embed=e)
            await self.bot.db.execute('UPDATE level SET level = $1, level_exp = $2 '
                                      'WHERE member_id = $3 AND guild_id = $4',
                                      lvl_end, exp_new, message.author.id, message.guild.id)

    @commands.slash_command(name='level')
    @option('member')
    async def level(self, ctx, member: Member = None):
        if not member:
            member = ctx.author
        stats = await self.bot.db.fetch('SELECT level, level_exp FROM level WHERE member_id = $1 AND guild_id = $2',
                                        member.id, ctx.guild.id)
        exp = stats[0]['level_exp']
        lvl = stats[0]['level']
        exp_need = (lvl+1)**4
        emb = Embed(title=f'Level: {lvl}', description=f'{exp}/{exp_need}', color=Color.green())
        emb.set_author(name=member.name, icon_url=member.avatar)
        await ctx.respond(embed=emb, delete_after=20)

    @commands.command(name='test')
    async def test(self, ctx):
        await draw_card_level(ctx.channel, ctx.author)


def setup(bot):
    bot.add_cog(Level(bot))
