from ext import update, utils
import datetime
import os
import json


class Config:
    """The class to handle the custom configurations of the bot."""

    def __init__(self, bot):
        self.bot = bot
        self.dir = os.path.join(bot.basedir, "ext/config")
        with open(os.path.join(bot.basedir, "data/jokes.json")) as f:
            self.bot.jokes = json.loads(f.read())
            f.close()
        with open(os.path.join(bot.basedir, "data/trivias.json")) as f:
            self.bot.trivias = json.loads(f.read())
            f.close()
        self.bot.bssounds = os.listdir(os.path.join(self.bot.basedir, "bssounds/"))

    async def get_guild_config(self, gid: str):
        """To find the config data of a guild."""
        return {"prefix": str(await self.get_prefix(gid)),
                "add_time": str(await self.get_guild_add_time(gid)),
                "bstats": await self.get_bstats(gid)}

    async def get_prefix(self, gid):
        """To get prefix for a guild."""
        rows: list = await utils.mysql_get(self.bot, gid)
        prefix = rows[0][1]
        return prefix

    async def get_guild_add_time(self, gid):
        """To get the time bot was added in this guild."""
        rows: list = await utils.mysql_get(self.bot, gid)
        time = rows[0][2]
        if isinstance(time, datetime.datetime):
            time = time.strftime('%Y-%m-%d %H:%M:%S')
        return time

    async def get_bstats(self, gid):
        """To get BombSquad stats configuration of a guild."""
        rows: list = await utils.mysql_get(self.bot, gid)
        return json.loads(str(rows[0][3]))

    async def update(self, gid: str, option, value):
        """Used to update config settings of a guild."""
        u = update.Update(self.bot, gid, option, value)
        await u.run()