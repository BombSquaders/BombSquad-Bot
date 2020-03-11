import discord
from discord.ext import commands
import datetime
import random
import json
import aiomysql
import os


async def get_user_vote(bot, user: int) -> bool:
    voted = False
    if bot.dbl_client is not None:

        # First check if the user is in bot's vote cache
        ud = bot.dbl_user_votes.get(str(user), {})
        voted = ud.get("voted", "undefined")
        now = datetime.datetime.utcnow()
        cache_time = ud.get("cache_time", now)

        # If not or if it is for longer than 15 minutes then retrieve a fresh vote data of the user
        if now - cache_time > datetime.timedelta(minutes=15) or voted == "undefined":
            voted = await bot.dbl_client.get_user_vote(user)

            # And save it to the cache if it is true
            if voted:
                bot.dbl_user_votes[str(user)] = {"voted": voted, "cache_time": datetime.datetime.utcnow()}
    return voted


async def get_user_data(bot, user: int) -> list:
    """To retrieve the current data of a user."""

    async def to_run() -> list:
        async with bot.db_pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM `users` WHERE id={user};")
                new = [user, 0, 0, {}, None, None]
                row = await cursor.fetchone()

                if not row:
                    # Create an entry for the player if there is None yet
                    await mysql_set(bot=bot, id=user, arg1="players", arg2="new")
                    return new  # Rerun the process of retrieving

                custom_bg = row[4] or "default.png"
                data = [int(row[0]), int(row[1]), int(row[2]), json.loads(str(row[3])), custom_bg, row[5]]
                return data  # Return the retrieved data if everything is fine

    try:
        return await to_run()
    # If any aiomysql error occurs or the pool is None due to connection errors or timeouts
    except (aiomysql.Error, AttributeError, TypeError):
        bot.db_pool = await aiomysql.create_pool(host='localhost',
                                                 db=os.environ.get("mysql_database"),
                                                 user=os.environ.get("mysql_user"),
                                                 password=os.environ.get("mysql_password"))
        return await to_run()


async def increment_ticket(bot, user: int, tickets: int = 1):
    d = await get_user_data(bot, user)
    await mysql_set(bot, str(user), arg1="players", arg2="tickets", arg3=f"{int(d[1]) + tickets}")


def test_channel():
    def wrapper(ctx):
        with open('data/test-channels.json') as f:
            channels = json.load(f)
        if ctx.channel.id in channels:
            return True
        raise commands.MissingPermissions('You cannot use this command outside the beta commands test channel.')

    return commands.check(wrapper)


def developer():
    def wrapper(ctx):
        with open('data/devs.json') as f:
            developers = json.load(f)
        if ctx.author.id in developers:
            return True
        raise commands.MissingPermissions('You cannot use this command because you are not a developer.')

    return commands.check(wrapper)


def paginate(text: str):
    """Simple generator that paginates text."""
    last = 0
    pages = []
    appd_index = 0
    curr = 0
    for curr in range(0, len(text)):
        if curr % 1980 == 0:
            pages.append(text[last:curr])
            last = curr
            appd_index = curr
    if appd_index != len(text) - 1:
        pages.append(text[last:curr])
    return list(filter(lambda a: a != '', pages))


def cleanup_code(content):
    """Automatically removes code blocks from the code."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    return content.strip('` \n')


def random_color() -> discord.Colour:
    """Provides a random discord.Color value"""
    color = ('#%06x' % random.randint(8, 0xFFFFFF))
    color = int(color[1:], 16)
    color = discord.Color(value=color)
    return color


async def mysql_get(bot, server_id: str) -> list:
    """Get data from a table in the bot's MySQL database"""

    async def to_run() -> list:
        async with bot.db_pool.acquire() as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(f"SELECT * FROM `servers` WHERE id={server_id};")
                new = [server_id, bot.default_prefix, datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), '{}',
                       None,
                       0]
                data = await cursor.fetchone()

                if not data:  # Passes if the database does not have any entry for the asked server
                    await mysql_set(bot, server_id,
                                    arg3="join")  # Create an entry for the discord server if there is None yet
                    return new  # Return the new data of the server

                return data  # Return the retrieved data if everything is fine

    try:
        return await to_run()
    # If any aiomysql error occurs or the pool is None due to connection errors or timeouts
    except (aiomysql.Error, AttributeError, TypeError):
        bot.db_pool = await aiomysql.create_pool(host='localhost',
                                                 db=os.environ.get("mysql_database"),
                                                 user=os.environ.get("mysql_user"),
                                                 password=os.environ.get("mysql_password"))
        return await to_run()


async def mysql_set(bot, id: str, arg1: str = None, arg2: str = None, arg3: str = None):
    """Set data to a table in the bot's MySQL database"""

    async def to_run():
        async with bot.db_pool.acquire() as connection:
            async with connection.cursor() as cursor:
                if arg3 == "join":
                    await cursor.execute(
                        "INSERT INTO `servers` (`id`, `prefix`, `add_time`, `bs_stats`, `spawn_channels`, "
                        f"`random_events`) VALUES ('{id}', 'bs!', '"
                        f"{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}','{{}}', NULL, 0);")
                elif arg3 == "remove":
                    await cursor.execute(f"DELETE FROM `servers` WHERE id={id};")
                else:
                    if arg1 == "prefix":
                        await cursor.execute(f"UPDATE `servers` SET prefix='{arg2}' WHERE id={id};")
                    if arg1 == "spawn_channel":
                        await cursor.execute(f"UPDATE `servers` SET spawn_channels={arg2} WHERE id={id};")
                    if arg1 == "random_events":
                        await cursor.execute(f"UPDATE `servers` SET random_events={arg2} WHERE id={id};")
                    elif arg1 == "bs_stats":
                        await cursor.execute(f"UPDATE `servers` SET bs_stats='{arg2}' WHERE id={id};")
                    elif arg1 == "fan_arts":
                        await cursor.execute(
                            f"INSERT INTO `fan_arts` (`username`, `img_url`, `send_time`) VALUES ('{id}', '{arg2}', '{arg3}');")
                    elif arg1 == "players":
                        if arg2 == "new":
                            await cursor.execute(
                                "INSERT INTO `users` (`id`, `tickets`, `bombs`, `powers`, `custom_bg`, `dead`) VALUES "
                                f"('{id}', 50, 1, '{{}}', NULL, NULL);")
                        else:
                            await cursor.execute(
                                f"UPDATE `users` SET {arg2}={arg3} WHERE id={id};")
                    else:
                        return await cursor.close()
                await connection.commit()

    try:
        await to_run()
        # If any aiomysql error occurs or the pool is None due to connection errors or timeouts
    except (aiomysql.Error, AttributeError, TypeError):
        bot.db_pool = await aiomysql.create_pool(host='localhost',
                                                 db=os.environ.get("mysql_database"),
                                                 user=os.environ.get("mysql_user"),
                                                 password=os.environ.get("mysql_password"))
        await to_run()
