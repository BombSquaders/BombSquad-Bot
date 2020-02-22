import discord
from discord.ext import commands
import datetime
import random
import json
import mysql.connector
import os


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

    async def to_run():
        bot.MySQLConnection.cmd_refresh(1)
        bot.MySQLCursor.execute(f"SELECT * FROM `servers` WHERE id={server_id};")
        new = [(server_id, bot.default_prefix, datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), "0", None, {})]
        data = bot.MySQLCursor.fetchall()

        if len(data) == 0:  # Passes if the database does not have any entry for the asked server
            await mysql_set(bot, server_id, arg3="join")  # Create an entry for the discord server if there is None yet
            return new  # Rerun the process of retrieving

        return data  # Return the retrieved data if everything is fine

    try:
        return await to_run()
    except mysql.connector.errors.ProgrammingError:
        bot.MySQLConnection = mysql.connector.connect(host='localhost',
                                                      database=os.environ.get("mysql_database"),
                                                      user=os.environ.get("mysql_user"),
                                                      password=os.environ.get("mysql_password"))
        bot.MySQLCursor = bot.MySQLConnection.cursor()
        return await to_run()


async def mysql_set(bot, id: str, arg1: str = None, arg2: str = None, arg3: str = None):
    """Set data to a table in the bot's MySQL database"""

    async def to_run():
        if arg3 == "join":
            bot.MySQLCursor.execute("INSERT INTO `servers` (`id`, `prefix`, `add_time`, `bs_stats`) VALUES "
                                    f"('{id}', 'bs!', '{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}',"
                                    "'{}');")
        elif arg3 == "remove":
            bot.MySQLCursor.execute(f"DELETE FROM `servers` WHERE id={id};")
        else:
            if arg1 == "prefix":
                bot.MySQLCursor.execute(f"UPDATE `servers` SET prefix='{arg2}' WHERE id={id};")
            elif arg1 == "bs_stats":
                bot.MySQLCursor.execute(f"UPDATE `servers` SET bs_stats='{arg2}' WHERE id={id};")
            elif arg1 == "fan_arts":
                bot.MySQLCursor.execute(
                    f"INSERT INTO `fan_arts` (`username`, `img_url`, `send_time`) VALUES ('{id}', '{arg2}', '{arg3}');")
        bot.MySQLConnection.commit()

    try:
        await to_run()
    except mysql.connector.errors.ProgrammingError:
        bot.MySQLConnection = mysql.connector.connect(host='localhost',
                                                      database=os.environ.get("mysql_database"),
                                                      user=os.environ.get("mysql_user"),
                                                      password=os.environ.get("mysql_password"))
        bot.MySQLCursor = bot.MySQLConnection.cursor()
        await to_run()
