import discord
from discord import Embed

from discord.ext import commands
from discord.utils import get

from config.envirorment import OWNER, VERSION,  BOT

from config.util import get_prefix, send_embed


def cmd_aliases(command):
    if command.aliases:
        return "**Aliases:** " + ", ".join(command.aliases)
    return ""


def cmd_params(command):
    params = []
    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "None" in str(value) else f"<{key}>")
    return " ".join(params)


class Help(commands.Cog, description="Zeigt diese Help Nachricht an"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help",
                      description="Zeigt alle Module dieses Bots an",
                      help="help [Modul]")
    async def help(self, ctx, *input):
        await ctx.channel.purge(limit=1)
        prefix = await get_prefix(self.bot, ctx.message)
        owner_name = get(ctx.guild.members, id=OWNER).name
        bot_name = get(ctx.guild.members, id=BOT).name

        # checks if cog parameter was given
        # if not: sending all modules and commands not associated with a cog
        if not input:
            # checks if owner is on this server - used to 'tag' owner
            try:
                owner = ctx.guild.get_member(OWNER).mention

            except AttributeError as e:
                owner = OWNER

            # starting to build embed
            emb = Embed(title=f'{bot_name}´s Hilfe', color=discord.Color.blue(),
                                description=f'***`{prefix}help <Modul>`*** für mehr Information über das Modul :smiley:\n')

            # iterating trough cogs, gathering descriptions
            cogs_desc = ''
            for cog in self.bot.cogs:
                if (cog == "Admin" or cog == "GlobalChat") and ctx.author.id != OWNER:
                    pass
                    # cogs_desc = "You don´t have permissions to use these commands"
                else:
                    cogs_desc += f'`{cog}` \n *{self.bot.cogs[cog].description}*\n\n'

            # adding 'list' of cogs to embed
            emb.add_field(name='Module', value=cogs_desc, inline=False)

            # integrating trough uncategorized commands
            commands_desc = ''
            for command in self.bot.walk_commands():
                # if cog not in a cog
                # listing command if cog name is None and command isn't hidden
                if not command.cog_name and not command.hidden:
                    commands_desc += f'{command.name} - {command.description}\n'

            # adding those commands to embed
            if commands_desc:
                emb.add_field(name='Kein Modul', value=commands_desc, inline=False)

            # setting information about author
            emb.add_field(name="Über", value=f"Der Bot wird entwickelt von {owner_name}, basierend auf discord.py.\n\
                                            Diese Version wird gepflegt von {owner}")
            emb.set_footer(text=f"Bot Version: V{VERSION}")

        # block called when one cog-name is given
        # trying to find matching cog and it's commands
        elif len(input) == 1:
            inp = input[0]

            # embed if wether the cog nor the command can be found
            not_found = Embed(title="Was ist das?!",
                                    description=f"Von `{input[0]}` habe ich zuvor noch nichts gehört :scream:",
                                    color=discord.Color.orange())

            # check if input is in cogs list
            if inp in self.bot.cogs:
                # check if cog is the matching one
                if (inp == "Admin" or "GlobalChat") and ctx.author.id != OWNER:
                    emb = discord.Embed(title="Keine Berechtigung", color=discord.Color.red())
                else:
                    desc = f'***`{prefix}help <Befehl>`*** für mehr Information über den Befehl :smiley:\n\n'

                    # getting commands from cog
                    for command in self.bot.get_cog(inp).get_commands():
                        brief = "\u200b"
                        if command.brief:
                            brief = f"- {command.brief}"
                        elif command.description:
                            brief = f"- {command.description}"
                        # if cog is not hidden
                        if not command.hidden:
                            desc += f"`{prefix}{command.name}` *{brief}* \n\n"
                    emb = Embed(title=f'{inp} - Befehle', description=desc, color=discord.Color.green())
            else:
                for command in self.bot.commands:
                    if str(command) == inp:
                        if (command.cog_name == "Admin" or "GlobalChat") and ctx.author.id != OWNER:
                            emb = Embed(title="Keine Berechtigung", color=discord.Color.red())
                            break

                        desc = f"{command.description} \n\n"
                        name = f"{prefix}{command.name} {cmd_params(command)}\n"
                        aliases = f"{cmd_aliases(command)} \n\n"
                        help = command.help
                        emb = Embed(description=desc+name+aliases+help)
                        break
                else:
                    emb = not_found

        # too many cogs requested - only one at a time allowed
        elif len(input) > 1:
            emb = Embed(title="Das ist zu viel.",
                                description="Bitte frage nur ein Modul zur Zeit an :sweat_smile:",
                                color=discord.Color.orange())

        else:
            emb = Embed(title="Ein magischer Ort.",
                                description="Wie du hergefunden hast ist mir ein Rätsel. Das habe ich nicht kommen sehen.\n"
                                            "Hilf mir dieses Rätsel zu lösen und schreibe mir wie du hergefunden hast.\n"
                                            "https://github.com/nonchris/discord-fury/issues\n"
                                            "Danke dir! ~Stefan aka PeeT_Tea",
                                color=discord.Color.red())

        # sending reply embed using our own function defined above
        # await send_embed(ctx, emb)
        await ctx.send(embed=emb)


############################################################
def setup(bot):
    bot.add_cog(Help(bot))
