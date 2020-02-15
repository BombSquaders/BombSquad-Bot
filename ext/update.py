from ext import utils


class Update:
    """Used to update the config settings of a guild in the MySql database."""

    def __init__(self, bot, gid: str, option: str, value: str):
        self.bot = bot
        self.gid = gid
        self.option = option
        self.value = value

    async def run(self):
        if self.option == "prefix":
            await self.prefix()
        elif self.option == "BSStats":
            await self.bs_stats()
        elif self.option == "guild":
            await self.guild()

    async def guild(self):
        if self.value == "join":
            await utils.mysql_set(self.bot, self.gid, arg3="join")
        elif self.value == "remove":
            await utils.mysql_set(self.bot, self.gid, arg3="remove")

    async def prefix(self):
        """Used to update the bot's prefix of a guild."""
        await utils.mysql_set(self.bot, self.gid, arg1="prefix", arg2=self.value)

    async def bs_stats(self):
        """Used to update the bot's BS stats configuration of a guild."""
        await utils.mysql_set(self.bot, self.gid, arg1="bs_stats_url", arg2=self.value)
