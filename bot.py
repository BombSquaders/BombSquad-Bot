#!/usr/bin/env python3.8
import discord
from discord.ext import commands
import dbl
from ext import utils, config
from ext.utils import increment_ticket
from ext.paginator import PaginatorSession
import traceback
from datetime import datetime, timedelta
import asyncio
import os
from threading import Thread
import sys
import aiomysql

from typing import List, Any, Dict, Optional

# The extensions to be added to our bot
extensions: List[str] = [x.replace('.py', '') for x in os.listdir('cogs') if x.endswith('.py')]


# A function to get the prefix of the bot for a message
async def prefix(d_client, message) -> str:
    """Get prefix"""
    # This line lets the users either use mention or characters for command prefix
    return commands.when_mentioned_or(await d_client.config.get_prefix(message.guild.id))(d_client, message)
    # Comment the above line and use just 'return await d_client.config.get_prefix(message.guild.id)' if you do not want
    # the bot to respond to commands with bot mention as prefix


# A Thread to get the commands input from the terminal after running the bot
class RunInput(Thread):
    def run(self) -> None:
        global inpt
        que: bool = False
        cmd: str = ""
        while inpt:
            command = str(sys.stdin.readline()).rstrip()
            if not que:
                if command.endswith(":"):  # For a multi line command
                    que = True
                    cmd = command + "\n"
                else:  # Execute a simple command when we are not registering multiple lines
                    cmd = ""
                    try:
                        exec(command)
                    except Exception:
                        traceback.print_exc()
            else:
                if command == "":  # End adding multi line command after a blank line is given and execute it
                    que = False
                    try:
                        exec(cmd)
                    except Exception:
                        traceback.print_exc()
                    cmd = ""
                else:  # Continue adding to multiline command
                    cmd += command + "\n"


t: Thread
inpt: bool = False


class BotCreator(object):
    """Just a class to contain the creator info."""
    github = "https://www.github.com/BombSquaders/"  # The Github account url
    bot_github = f"{github}BombSquad-Bot/"  # The repository name of this bot's source code on Github
    name = f"[BombSquaders organization]({github})"  # The creator name here
    url = "https://www.rahulraman.me/"  # The website or web-page of the creator here
    icon = "https://avatars1.githubusercontent.com/u/62781896"  # The icon url
    patreon = "https://patreon.com/rahulraman0108"  # The patreon page of the creator
    discord = 473128022711730177  # Discord id snowflake of the creator's discord account
    support_server = "https://discord.gg/dNX2P2k"  # The bot's support discord server invite
    bot_invite_perms = "36981824"


# Our bot instance, use commands.AutoShardedBot if the bot passes 1000 server
class MyBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

        self.remove_command("help")  # We will add a new help command for our bot later

        self.basedir: str = os.path.dirname(os.path.abspath(__file__))
        os.chdir(self.basedir)

        self.creator: BotCreator = BotCreator()  # Set the Bot Creator attribute
        self.default_prefix: str = "bs!"  # The bot's default prefix for new servers
        self.db_pool: Optional[aiomysql.Pool] = None
        self.dbl_token: Optional[str] = os.environ.get("bot_dbl_token", None)  # The Discord Bot List token
        self.dbl_user_votes: Dict[str, Any] = {}  # For caching the users who upvote the bot

        # For granting tickets on messaging every 1 minute
        self.recent_tickets: Dict[str, datetime] = {}

        # Now setting some custom attributes for our bot for later use
        self.announcement: Optional[str] = None
        self.config: Optional[config.Config] = None
        self.dbl_client: Optional[dbl.DBLClient] = None

        self.tt: timedelta = timedelta(minutes=2)


bot: MyBot = MyBot(command_prefix=prefix,
                   description=f"A discord bot made by {BotCreator.name} having special brand new "
                               f"features related to the BombSquad game.")


@bot.event
async def on_connect() -> None:
    global t, inpt
    inpt = False  # Just for surety to that the thread is not running
    await asyncio.sleep(0.005)
    # Set the variable t it should be a new instance of the input thread now
    t = RunInput()
    t.daemon = True

    ex: List[str] = [x for x in bot.extensions]  # Make a copy of list so it don't change while unloading
    for extension in ex:  # Unload any loaded extension
        bot.unload_extension(extension)

    bot.config = config.Config(bot)

    for e in extensions:  # Load available extensions
        bot.load_extension("cogs." + e)

    if not bot.db_pool:
        bot.db_pool = await aiomysql.create_pool(host='localhost',
                                                 db=os.environ.get("mysql_database"),
                                                 user=os.environ.get("mysql_user"),
                                                 password=os.environ.get("mysql_password"))

    if bot.dbl_client is not None:  # Make it sure that it is None, we will set it in on_ready func
        await bot.dbl_client.close()
        bot.dbl_client = None


@bot.event
async def on_disconnect() -> None:
    global inpt
    inpt = False  # Stop reading input from terminal

    if bot.dbl_client is not None:  # Stop the DBL client because we are disconnected from discord
        await bot.dbl_client.close()
        bot.dbl_client = None


@bot.event
async def on_ready() -> None:
    global inpt, t

    await bot.change_presence(status=discord.Status.offline)  # Change to offline when loading
    print(f"Logged in.\n"
          f"-----------------------\n"
          f"Name: {bot.user.name}\n"
          f"ID: {bot.user.id}\n")

    if bot.dbl_token is not None:  # If our bot is listed on DBL and we have the token then initiate DBL client
        bot.dbl_client = dbl.DBLClient(bot, bot.dbl_token, webhook_port=5000)

    print("Ready for use.")

    await bot.change_presence(activity=discord.Game(name=f"in {len(bot.guilds)} servers | bs!help", type=2),
                              status=discord.Status.online, afk=True)  # The bot is ready to use

    if bot.dbl_client is not None:  # If we have our DBL client then post the servers count and cache the bot upvotes
        await bot.dbl_client.post_guild_count()
        for u in await bot.dbl_client.get_bot_upvotes():
            bot.dbl_user_votes[str(u["id"])] = {"voted": True, "cache_time": datetime.utcnow()}

    if not inpt:  # If we are not reading input from the terminal then start reading it
        inpt = True
        t.start()


@bot.event
async def on_dbl_vote(data: Dict[str, Any]) -> None:
    uid = data["user"]
    print("DBL vote received")
    await increment_ticket(bot, uid)
    bot.dbl_user_votes[str(uid)] = {"voted": True, "cache_time": datetime.utcnow()}


@bot.event
async def on_dbl_test(data: Any) -> None:
    print("DBL test vote received")
    print(data)


@bot.event
async def on_command_error(ctx: commands.Context, error: Exception) -> None:
    # Errors for which the user needs help
    send_help: tuple = (
        commands.MissingRequiredArgument, commands.BadArgument, commands.TooManyArguments, commands.UserInputError)
    em: discord.Embed

    if isinstance(error, commands.CommandNotFound):  # Fails silently
        pass

    elif isinstance(error, discord.Forbidden):  # What could we possibly do if we are forbidden to do anything
        pass

    elif isinstance(error, send_help):
        help_message: discord.Embed = await send_cmd_help(ctx)
        await ctx.send(embed=help_message)

    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            f'This command is on `{error.cooldown.type}` type cooldown. Please wait {error.retry_after:.2f}s')

    elif isinstance(error, commands.MissingPermissions):
        em = discord.Embed(title="Lacking permission",
                           description=f'You do not have the necessary permissions to use this command.',
                           color=discord.colour.Color.red())
        em.add_field(name="Missing Permission:", value=str(error.missing_perms))
        await ctx.send(embed=em)

    elif isinstance(error, commands.BotMissingPermissions):
        em = discord.Embed(title="Lacking permission",
                           description=f'I do not have the necessary permissions to execute this command either in this'
                                       f' discord channel or server.',
                           color=discord.colour.Color.red())
        em.add_field(name="Missing Permission:", value=str(error.missing_perms))
        await ctx.send(embed=em)

    # If any other error occurs, prints to console.
    else:
        print(''.join(traceback.format_exception(type(error), error, error.__traceback__)))


@bot.event
async def on_message(message: discord.Message) -> None:
    if not bot.is_ready() or message.author.bot or isinstance(message.channel, discord.DMChannel) or isinstance(
            message.channel, discord.GroupChannel):
        return

    now: datetime = datetime.utcnow()
    if not bot.recent_tickets.get(str(message.author.id), now - bot.tt) > now - bot.tt:
        # Check if the ticket to this user was last granted 2 minutes ago
        await increment_ticket(bot, message.author.id)
        bot.recent_tickets[str(message.author.id)] = now

    await bot.process_commands(message)


@bot.event
async def on_guild_join(g: discord.Guild) -> None:
    await bot.config.update(str(g.id), "guild", "join")
    success: bool = False
    i: int = 0
    # Try to send a thank you message to the right channel in the server
    while not success:
        try:
            p: str = await bot.config.get_prefix(g.id)
            await g.channels[i].send(
                f"Hello! Thanks for inviting me to your server. To set a custom prefix, use `{p}prefix"
                f" <prefix>`. For more help, use `{p}help`.")
        except (discord.Forbidden, AttributeError):
            i += 1
        except IndexError:
            # if the server has no channels, doesn't let the bot talk, or all vc/categories
            pass
        else:
            success = True

    await bot.change_presence(activity=discord.Game(f"in {len(bot.guilds)} servers | {bot.default_prefix}help"),
                              afk=True)

    if bot.dbl_client is not None:
        await bot.dbl_client.post_guild_count()


@bot.event
async def on_guild_remove(g: discord.Guild) -> None:
    await bot.config.update(str(g.id), "guild", "remove")
    await bot.change_presence(activity=discord.Game(f"in {len(bot.guilds)} servers | {bot.default_prefix}help"),
                              afk=True)

    if bot.dbl_client is not None:
        await bot.dbl_client.post_guild_count()


async def send_cmd_help(ctx: commands.Context) -> discord.Embed:
    cmd: commands.Command = ctx.command
    p: str = str(cmd.root_parent) + " " if cmd.root_parent is not None else ""
    pre: str = await bot.config.get_prefix(ctx.guild.id)
    em: discord.Embed = discord.Embed(title=f'Usage: `{pre + p + cmd.name} {cmd.signature}`',
                                      color=utils.random_color())
    em.description = cmd.help
    return em


def format_cog_help(cog_name: str, em: discord.Embed) -> discord.Embed:
    """Format help for a cog"""
    cog_commands: List[commands.Command] = bot.get_cog(cog_name).get_commands()
    commands_list: str = ''
    for comm in cog_commands:
        if not comm.hidden:
            commands_list += f'**{comm.name}** - *{comm.short_doc}* \n'

    em.add_field(
        name=f"{cog_name}",
        value=commands_list,
        inline=False
    ).add_field(
        name='\u200b', value='\u200b', inline=False
    )

    return em


async def format_command_help(ctx: commands.Context, cmd: commands.Command, em: discord.Embed) -> discord.Embed:
    """Format help for a command"""

    pre: str = await bot.config.get_prefix(ctx.guild.id)
    p: str = str(cmd.root_parent) + " " if cmd.root_parent is not None else ""
    c: str

    if getattr(cmd, 'invoke_without_command', False):
        c = f'`{pre + p + cmd.name} {cmd.signature} <sub-command> [args]`'
    else:
        c = f'`{pre + p + cmd.name} {cmd.signature}`'
    em.add_field(name="Usage syntax:", value=c, inline=False) \
        .add_field(name="Description:", value=cmd.short_doc, inline=False) \
        .add_field(name='\u200b', value='\u200b', inline=False)

    return em


async def format_bot_help(ctx: commands.Context) -> discord.Embed:
    signatures: List[int] = []
    fmt: str = ''
    bot_commands: List[commands.Command] = []
    pre: str = await bot.config.get_prefix(ctx.guild.id)
    for cmd in bot.commands:
        if not cmd.hidden:
            if not cmd.cog:
                bot_commands.append(cmd)
                signatures.append(len(cmd.name) + len(pre))
    max_length: int = max(signatures)
    abc: List[commands.Command] = sorted(bot_commands, key=lambda x: x.name)
    for c in abc:
        fmt += f'`{pre + c.name:<{max_length}} '
        fmt += f'{c.short_doc:<{max_length}}`\n'
    em: discord.Embed = discord.Embed(title='Bot', color=utils.random_color())
    em.set_thumbnail(url=bot.user.avatar_url)
    em.description = '*Commands for the main bot.*'
    em.add_field(name='Commands', value=fmt)

    return em


@bot.command(name="help", aliases=['commands', 'command'], usage='cog')
async def _help(ctx: commands.Context, *, command: str = None) -> None:
    """Shows this message"""

    pages: List[discord.Embed] = []
    pre: str = await bot.config.get_prefix(ctx.guild.id)

    if command is not None:
        cog: Optional[commands.Cog] = bot.get_cog(command.replace(' ', '_').title())
        cmd: Optional[commands.Command] = bot.get_command(command)
        em = discord.Embed(
            title=f'`{command}` Help',
            color=utils.random_color()
        )
        em.set_thumbnail(url=bot.user.avatar_url)
        em.set_footer(
            text=f'Type `{pre}help <command>` for more info on a command.',
            icon_url=bot.user.avatar_url
        )

        if cog is not None and not getattr(cog, "hidden", False):
            em = format_cog_help(command.replace(' ', '_').title(), em)
        elif cmd is not None:
            em = await format_command_help(ctx, cmd, em)
        else:
            await ctx.send('No commands or cog found which satisfies the name you gave.')
            return

        await ctx.send(embed=em)
        return

    pages.append(await format_bot_help(ctx))

    cog_n: str
    em: discord.Embed
    for cog_n in bot.cogs:
        em = discord.Embed(
            title='Help',
            color=utils.random_color()
        )
        em.set_thumbnail(url=bot.user.avatar_url)
        em = format_cog_help(cog_n, em)
        if not getattr(bot.cogs[cog_n], "hidden", False):
            pages.append(em)

    p_session: PaginatorSession = PaginatorSession(ctx,
                                                   footer=f'Type `{pre}help <command>` for more info on a command.',
                                                   pages=pages)
    await p_session.run()

    return


@bot.command()
async def ping(ctx: commands.Context) -> None:
    """Pong! Get the bot's response time"""
    em = discord.Embed(color=discord.Color.green())
    em.title = "Pong!"
    em.description = f'{bot.latency * 1000} ms'
    await ctx.send(embed=em)


@bot.command(name='bot')
async def _bot(ctx: commands.Context) -> None:
    """Shows info about bot"""
    em: discord.Embed = discord.Embed(color=discord.Color.green())
    em.title = 'Bot Info'
    em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    p: str = bot.announcement if bot.announcement is not None else bot.description
    em.description = p + f'\n[Support Server]({bot.creator.support_server})'
    em.add_field(name="Servers", value=str(len(bot.guilds)))
    em.add_field(name="Online Users",
                 value=str(len(
                     {m.id for m in bot.get_all_members() if m.status is not discord.Status.offline and not m.bot})))
    em.add_field(name='Total Users', value=str(len({m.id for m in bot.get_all_members() if not m.bot})))
    em.add_field(name='Channels', value=f"{sum(1 for g in bot.guilds for _ in g.channels)}")
    em.add_field(name="Library", value=f"discord.py")
    em.add_field(name="Bot Latency", value=f"{bot.ws.latency * 1000:.0f} ms")
    em.add_field(name="Invite link",
                 value=f"[Invite the bot to any server](https://discordapp.com/oauth2/authorize?client_id={bot.user.id}"
                       f"&scope=bot&permissions={bot.creator.bot_invite_perms})")
    em.add_field(name='GitHub', value=f'[BombSquad Bot Github]({bot.creator.bot_github})')
    em.add_field(name="Discord Bots List",
                 value=f"[Upvote this bot!](https://top.gg/bot/{bot.user.id}) :reminder_ribbon:")
    em.add_field(name="Support the creator!",
                 value=f"[Creator's Patreon Page]({bot.creator.patreon}) :reminder_ribbon:")

    em.set_footer(text="BombSquad Bot | Powered by discord.py")
    await ctx.send(embed=em)


@bot.command()
async def creator(ctx: commands.Context) -> None:
    """Shows bot's creator"""
    em: discord.Embed = discord.Embed(title="BombSquad Bot creator",
                                      description=f"I am created by the {bot.creator.name}.")
    em.set_author(name=bot.creator.name, url=bot.creator.url, icon_url=bot.creator.icon)
    em.add_field(name="Support the creator", value=f"[Patreon Page]({bot.creator.patreon})")
    em.set_footer(text="BombSquad Bot | Powered by discord.py")
    await ctx.send(embed=em)


@bot.command()
async def invite(ctx: commands.Context) -> None:
    """Shows invite link of the bot"""
    em: discord.Embed = discord.Embed(color=utils.random_color())
    em.title = 'Bot Invite Link'
    em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    p: str = bot.announcement if bot.announcement is not None else bot.description
    em.description = p + f'\n[Support Server]({bot.creator.support_server})'
    em.add_field(name="Invite the bot",
                 value=f"[Invite this bot to a server](https://discordapp.com/oauth2/authorize?client_id={bot.user.id}"
                       + f"&scope=bot&permissions={bot.creator.bot_invite_perms})")
    em.add_field(name="Support the creator", value=f"[Patreon Page]({bot.creator.patreon})")
    em.set_footer(text="BombSquad Bot | Powered by discord.py")
    await ctx.send(embed=em)


@bot.command()
async def support(ctx: commands.Context) -> None:
    """Get the support server's invite link."""
    em: discord.Embed = discord.Embed(color=utils.random_color())
    em.title = 'Our support server'
    em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    p: str = bot.announcement if bot.announcement is not None else bot.description
    em.description = p + f'\n[Support Server]({bot.creator.support_server})'
    em.add_field(name="Support Server",
                 value=f"[Click Here]({bot.creator.support_server})")
    em.add_field(name="Invite the bot",
                 value=f"[Click Here](https://discordapp.com/oauth2/authorize?client_id={bot.user.id}"
                       + f"&scope=bot&permissions={bot.creator.bot_invite_perms})")
    em.add_field(name="Support the creator", value=f"[Patreon Page]({bot.creator.patreon})")
    em.set_footer(text="BombSquad Bot | Powered by discord.py")
    await ctx.send(embed=em)


@bot.command(aliases=['upvote'])
async def vote(ctx: commands.Context) -> None:
    """Shows vote link of the bot"""
    em: discord.Embed = discord.Embed(color=utils.random_color())
    em.title = 'Bot Voting Link'
    em.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
    p: str = bot.announcement if bot.announcement is not None else bot.description
    em.description = p + f'\n[Support Server]({bot.creator.support_server})'
    em.add_field(name="Upvote on Discord Bots List",
                 value=f"[Upvote this bot](https://top.gg/bot/{bot.user.id})")
    em.set_footer(text="BombSquad Bot | Powered by discord.py")
    await ctx.send(embed=em)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(bot.start(os.environ.get('bot_discord_token')))
    except KeyboardInterrupt:
        loop.run_until_complete(bot.logout())  # Cancel all tasks lingering
    finally:
        loop.close()
