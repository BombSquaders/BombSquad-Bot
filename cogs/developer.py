import discord
from discord.ext import commands
import io
import os
import asyncio
from contextlib import redirect_stdout
import textwrap
import traceback
import inspect
from ext import utils
from ext.utils import get_user_data
import datetime
import json


class Developer(commands.Cog):
    """Useful and utility commands."""

    def __init__(self, bot):
        self.hidden = True
        self.last_result = None
        self.bot = bot
        self.extensions = [x.replace('.py', '') for x in os.listdir('cogs') if x.endswith('.py')]

    @commands.command(name='presence', hidden=True)
    @utils.developer()
    async def _presence(self, ctx, option=None, *, value=None):
        """Change the bot's presence"""

        # One fo the developer only command to change the bot's presence
        if option is None:
            await ctx.send(f'Usage: `{ctx.prefix}presence [game/stream/watch/listen] [message]`')
        else:
            if option.lower() == 'stream':
                v = str(value).split("||-sep-||")
                await self.bot.change_presence(
                    activity=discord.Streaming(name=str(v[0]).strip(), url=str(v[1]).strip()),
                    status='online')
                await ctx.send(f'Set presence to. `Streaming {value}`')
            elif option.lower() == 'game':
                await self.bot.change_presence(activity=discord.Game(name=value))
                await ctx.send(f'Set presence to `Playing {value}`')
            elif option.lower() == 'watch':
                await self.bot.change_presence(activity=discord.Activity(name=value, type=3), afk=True)
                await ctx.send(f'Set presence to `Watching {value}`')
            elif option.lower() == 'listen':
                await self.bot.change_presence(activity=discord.Activity(name=value, type=2), afk=True)
                await ctx.send(f'Set presence to `Listening to {value}`')
            elif option.lower() == 'clear':
                await self.bot.change_presence(activity=None)
                await ctx.send('Cleared Presence')
            elif option.lower() == 'offline':
                await self.bot.change_presence(status=discord.Status.offline)
                await ctx.send('Done')
            elif option.lower() == 'online':
                await self.bot.change_presence(status=discord.Status.online)
                await ctx.send('Done')
            elif option.lower() == 'dnd':
                await self.bot.change_presence(status=discord.Status.do_not_disturb)
                await ctx.send('Done')
            elif option.lower() == 'idle':
                await self.bot.change_presence(status=discord.Status.idle)
                await ctx.send('Done')
            else:
                await ctx.send(f'Usage: `{ctx.prefix}presence [game/stream/watch/listen] [message]`')

    @commands.command(hidden=True)
    @utils.developer()
    async def source(self, ctx, command):
        """Get the source code for any command."""
        source = inspect.getsource(self.bot.get_command(command).callback)
        if not source:
            return await ctx.send(f'{command} is not a valid command.')
        try:
            await ctx.send(f'```py\n{source}\n```')
        except:
            paginated_text = utils.paginate(source)
            for page in paginated_text:
                if page == paginated_text[-1]:
                    await ctx.send(f'```py\n{page}\n```')
                    break
                await ctx.send(f'```py\n{page}\n```')

    @commands.command(hidden=True)
    @utils.developer()
    async def announce(self, ctx, *, message):
        """Tells everyone an announcement in the bot info command."""
        self.bot.announcement = None if str(message).lower() in ("reset", "clear", "none") else message
        await ctx.send('Announcement successfully set.')

    @commands.command(hidden=True)
    @utils.developer()
    async def grant(self, ctx, user: discord.User, item: str, amount: int):
        """To grant a discord user a certain amount of an item."""

        # The valid grant items
        t = "tickets"
        n_bombs = "bombs"
        gloves = "boxing_gloves"

        # Get the current data of the user
        data = await get_user_data(self.bot, user)

        if item in [x for x in self.bot.purchasables.keys() if str(x) != gloves and str(x) != n_bombs]:
            powers: dict = {}  # A dict to store the latest powerup data in
            now = datetime.datetime.utcnow()
            for key in data[3].keys():
                k_item = data[3][key]
                if not datetime.datetime.strptime(k_item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                    if str(key) == item:
                        expire = now + datetime.timedelta(days=2)
                        k_item["count"] = int(int(k_item["count"]) + amount)
                        k_item["expires"] = f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"
                    powers[key] = k_item

            # Make sure the powerup is in the dict
            if item not in powers.keys():
                value = {}
                expire = now + datetime.timedelta(days=2, hours=12)
                value["count"] = int(amount)
                value["expires"] = f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"
                powers[item] = value

            # At last, deduct the tickets and increment the granted item
            await utils.mysql_set(self.bot, user.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(powers))}'")
        elif item == gloves:
            powers: dict = {}  # A dict to store the latest powerup data in
            now = datetime.datetime.utcnow()
            for key in data[3].keys():
                value = data[3][key]
                if not datetime.datetime.strptime(value["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                    powers[key] = value

            # Now add the gloves
            expire = now + datetime.timedelta(days=2, hours=12)
            powers[gloves] = {"count": 1, "expires": f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"}

            # At last, deduct the tickets and increment the granted item
            await utils.mysql_set(self.bot, user.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(powers))}'")
        elif item == n_bombs:
            await utils.mysql_set(self.bot, user.id, arg1="players", arg2="bombs",
                                  arg3=f"{str(int(data[2]) + amount)}")
        elif item == t:
            await utils.mysql_set(self.bot, user.id, arg1="players", arg2="tickets",
                                  arg3=f"{str(int(data[1]) + amount)}")
        else:
            return await ctx.send(f"Unknown item {item}")

        # Success message
        await ctx.send(f"Successfully granted {amount} {item} to {user.name}.")

    # noinspection PyUnusedLocal
    @commands.command(name='py_val', hidden=True)
    @utils.developer()
    async def py_eval(self, ctx, *, body):
        """Evaluates python code (MUST ONLY BE ACCESSED BY THE OWNER)"""
        env = {
            'ctx': ctx,
            'bot': self.bot,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_': self.last_result,
            'source': inspect.getsource
        }

        env.update(globals())
        body = utils.cleanup_code(body)
        stdout = io.StringIO()
        err = out = None
        to_compile = f'async def func(): \n{textwrap.indent(body, "  ")}'
        try:
            exec(to_compile, env)
        except Exception as e:
            err = await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')
            return await ctx.message.add_reaction('\u2049')
        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            err = await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            if ret is None:
                if value:
                    try:
                        out = await ctx.send(f'```py\n{value}\n```')
                    except:
                        paginated_text = utils.paginate(value)
                        for page in paginated_text:
                            if page == paginated_text[-1]:
                                out = await ctx.send(f'```py\n{page}\n```')
                                break
                            await ctx.send(f'```py\n{page}\n```')
            else:
                self.bot.last_result = ret
                try:
                    out = await ctx.send(f'```py\n{value}{ret}\n```')
                except:
                    paginated_text = utils.paginate(f"{value}{ret}")
                    for page in paginated_text:
                        if page == paginated_text[-1]:
                            out = await ctx.send(f'```py\n{page}\n```')
                            break
                        await ctx.send(f'```py\n{page}\n```')
        if out:
            await ctx.message.add_reaction('\u2705')  # tick
        elif err:
            await ctx.message.add_reaction('\u2049')  # x
        else:
            await ctx.message.add_reaction('\u2705')

    @commands.command(hidden=True)
    @utils.developer()
    async def reload(self, ctx, cog):
        """Reloads a cog"""
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        if cog.lower() in ("all", "every"):
            for cog in self.extensions:
                try:
                    self.bot.unload_extension(f"cogs.{cog}")
                except Exception as e:
                    await ctx.send(f"An error occurred while reloading {cog}, error details: \n ```{e}```")
            for ex in self.extensions:
                self.bot.load_extension("cogs." + ex)
            return await ctx.send('All cogs updated successfully :white_check_mark:')
        if cog not in self.extensions:
            return await ctx.send(f'Cog {cog} does not exist.')
        try:
            self.bot.unload_extension(f"cogs.{cog}")
            await asyncio.sleep(1)
            self.bot.load_extension(f"cogs.{cog}")
        except Exception as e:
            await ctx.send(f"An error occurred while reloading {cog}, error details: \n ```python"
                           f"\n{e}\n"
                           f"```")
        else:
            await ctx.send(f"Reloaded the {cog} cog successfully :white_check_mark:")


def setup(bot):
    bot.add_cog(Developer(bot))
