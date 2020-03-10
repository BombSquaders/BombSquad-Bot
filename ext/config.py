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
        with open(os.path.join(bot.basedir, "data/random-events.json")) as f:
            self.bot.r_events = json.loads(f.read())
            f.close()
        with open(os.path.join(bot.basedir, "data/purchasables.json")) as f:
            self.bot.purchasables = json.loads(f.read())
            f.close()
        self.bot.bssounds = os.listdir(os.path.join(self.bot.basedir, "bssounds/"))

    async def get_guild_config(self, gid: str) -> dict:
        """To find the config data of a guild."""
        row = await utils.mysql_get(self.bot, gid)
        time = row[2]

        if isinstance(time, datetime.datetime):
            time = time.strftime('%Y-%m-%d %H:%M:%S')

        return {"prefix": str(row[1]),
                "add_time": time,
                "bstats": json.loads(row[3]),
                "spawn_channels": int(row[4]),
                "random_events": int(row[5]) == 1}

    async def get_prefix(self, gid) -> str:
        """To get prefix for a guild."""
        row = await utils.mysql_get(self.bot, gid)
        prefix = str(row[1])
        return prefix

    async def get_guild_add_time(self, gid) -> str:
        """To get the time bot was added in this guild."""
        row = await utils.mysql_get(self.bot, gid)
        time = row[2]
        if isinstance(time, datetime.datetime):
            time = time.strftime('%Y-%m-%d %H:%M:%S')
        return time

    async def get_bstats(self, gid) -> dict:
        """To get BombSquad stats configuration of a guild."""
        row = await utils.mysql_get(self.bot, gid)
        return json.loads(str(row[3]))

    async def get_spawn_channel(self, gid) -> int:
        """To get BombSquad stats configuration of a guild."""
        row = await utils.mysql_get(self.bot, gid)
        return int(row[4])

    async def get_random_events(self, gid) -> bool:
        """To get BombSquad stats configuration of a guild."""
        row = await utils.mysql_get(self.bot, gid)
        return int(row[5]) == 1

    async def update(self, gid: str, option, value):
        """Used to update config settings of a guild."""
        u = update.Update(self.bot, gid, option, value)
        await u.run()
