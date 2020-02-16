import discord
from discord.ext import commands
from discord.ext.commands import BucketType
import datetime
import json
import io
import aiohttp
import pytz
import wikipedia
import inspect
from ext import utils, paginator


class Utility(commands.Cog):
    """Useful and utility commands."""

    def __init__(self, bot):
        self.bot = bot

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
                await self.bot.change_presence(activity=discord.Streaming(name=v[0], url=v[1]),
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

    @commands.group(aliases=["bombsquadmods", "bombsquad-mods", "mod-manager"], invoke_without_command=True)
    async def modmanager(self, ctx):
        """To search or list all the mods of BombSquad game in the mod manager."""
        await ctx.send(f"use this command as:\n"
                       f"i) `{ctx.prefix}{ctx.command} list` to get list of all.\n"
                       f"ii) `{ctx.prefix}{ctx.command} search <term>` to search for a term.")

    @modmanager.command()
    async def list(self, ctx):
        """To list all mods of BombSquad game."""

        # Get the data of the current available to download mods
        repo = "Mrmaxmeier/BombSquad-Community-Mod-Manager"
        url = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = json.loads(await resp.read())

        mods = data.get("mods", {})
        pages = []
        number = 0
        for mod in mods:
            # Add an embed page for each downloadable mod
            number += 1
            filename = str(mods[mod].get("filename", None))
            em = discord.Embed(title="Mods list of BombSquad Game",
                               description=f"{number} numbered BombSquad game's mods in the ModManager.",
                               color=utils.random_color())
            em.add_field(name=str(mod),
                         value=f"[Download Link](https://raw.githubusercontent.com/{repo}/master/mods/{filename})")
            pages.append(em)

        # Run the session
        p_session = paginator.PaginatorSession(ctx=ctx, timeout=120, pages=pages, color=utils.random_color(),
                                               footer="List of all BombSquad game's mods in the ModManager.")
        await p_session.run()

    @modmanager.command()
    async def search(self, ctx, *, search: str):
        """Search a mod in the BombSquad game's mod manager list."""

        # Get the downloadable mods
        repo = "Mrmaxmeier/BombSquad-Community-Mod-Manager"
        url = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = json.loads(await resp.read())
        mods = data.get("mods", {})

        em = discord.Embed(title=search, description=f"Search results for `{search}`.", color=utils.random_color())
        for mod in mods:
            if str(mod).lower().__contains__(search.lower()):
                # Loop through all mods and select the matching ones
                filename = str(mods[mod].get("filename", None))
                em.add_field(name=str(mod),
                             value=f"[Download Link](https://raw.githubusercontent.com/{repo}/master/mods/{filename})")
        await ctx.send(embed=em)

    @commands.group(aliases=["accessoriesmanager", "accessories-manager"], invoke_without_command=True)
    async def accessories(self, ctx):
        """Search an accessory or list all accessories in my made BombSquad game's official accessories archive."""
        await ctx.send(f"use this command as:\n"
                       f"i) `{ctx.prefix}{ctx.command} list` to get list of all.\n"
                       f"ii) `{ctx.prefix}{ctx.command} search <term>` to search for a term.")

    @accessories.command(name="list")
    async def _list(self, ctx):
        """To list all accessories of the BombSquad game."""

        # Get all available accessories
        repo = "I-Am-The-Great/BombSquad-Official-Accessory-Archive"
        url = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = json.loads(await resp.read())
        all_files = data.get("all-files", {})

        pages = []
        number = 0
        for accessory in all_files:
            # Add each accessory as an embed page
            number += 1
            filename = str(all_files[accessory].get("filename", None))
            author = str(all_files[accessory].get("author", None))
            name = str(all_files[accessory].get("name", None))
            em = discord.Embed(title="Accessories list of BombSquad Game",
                               description=f"{number} numbered BombSquad game's accessory in the AccessoriesArchive.",
                               color=utils.random_color())
            em.add_field(name="Accessory Name", value=name)
            em.add_field(name="Author", value=author)

            # If accessory is single file give download link
            if not all_files[accessory].get("isCollection", False):
                em.add_field(name="Download Link",
                             value=f"https://raw.githubusercontent.com/{repo}/master/all-files/{filename}")

            # Else give the link to view it on Github
            else:
                rdir = str(all_files[accessory].get("rdir", None))
                em.add_field(name="Github Link", value=f"https://github.com/{repo}/tree/master/all-files/{rdir}")

            pages.append(em)
        p_session = paginator.PaginatorSession(ctx=ctx, timeout=120, pages=pages, color=utils.random_color(),
                                               footer="List of all BombSquad game's accessory in the AccessoryArchive.")
        await p_session.run()

    @accessories.command(name="search")
    async def _search(self, ctx, *, search: str):
        """To search for an accessory in the list of all accessories."""

        # Get available accessories
        repo = "I-Am-The-Great/BombSquad-Official-Accessory-Archive"
        url = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = json.loads(await resp.read())
        all_files = data.get("all-files", {})

        # Add only those accessories that matches the search term
        em = discord.Embed(title=search, description=f"Search results for `{search}`.", color=utils.random_color())
        for accessory in all_files:
            if str(accessory).lower().__contains__(search.lower()):
                filename = str(all_files[accessory].get("filename", None))
                author = str(all_files[accessory].get("author", None))
                name = str(all_files[accessory].get("name", None))
                if not all_files[accessory].get("isCollection", False):
                    em.add_field(name=name,
                                 value=f"Author: {author}\n[Download Link](https://raw.githubusercontent.com/{repo}"
                                       f"/master/all-files/{filename})")
                else:
                    rdir = str(all_files[accessory].get("rdir", None))
                    em.add_field(name=name,
                                 value=f"Author: {author}\n[Github Link](https://github.com/{repo}/tree/master/all-"
                                       f"files/{rdir})")
        await ctx.send(embed=em)

    @commands.command()
    async def datetime(self, ctx, tz=None):
        """Get the current date and time for a time zone or UTC."""

        # Send the current datetime
        now = datetime.datetime.now(tz=pytz.UTC)
        if tz:
            try:
                now = now.astimezone(pytz.timezone(tz))
            except:
                em = discord.Embed(color=utils.random_color())
                em.title = "Invalid timezone"
                em.description = f'Please search for the list of timezones on google.'
                return await ctx.send(embed=em)
        await ctx.send(f'It is currently {now:%A, %B %d, %Y} at {now:%I:%M:%S %p}.')

    @commands.command(aliases=['wikipedia'])
    async def wiki(self, ctx, *, query):
        """Search up something on wikipedia"""
        em = discord.Embed(title=str(query), color=utils.random_color())
        em.set_footer(text='Powered by wikipedia.org')
        try:
            # Search the query on wikipedia
            result = wikipedia.summary(query)
            if len(result) > 2000:
                em.description = f"Result is too long. View the website [here](https://wikipedia.org/wiki/" \
                                 f"{query.replace(' ', '_')}), or just google the subject."
                return await ctx.send(embed=em)
            em.description = result
            await ctx.send(embed=em)
        except wikipedia.exceptions.DisambiguationError as e:
            options = '\n'.join(e.options)
            em.description = f"**Options:**\n\n{options}"
            await ctx.send(embed=em)
        except wikipedia.exceptions.PageError:
            em.description = 'Error: Page not found.'
            await ctx.send(embed=em)

    @commands.command()
    @commands.cooldown(1, 15, BucketType.user)
    async def feedback(self, ctx, *, idea: str):
        """Suggest an idea, or complain an issue."""
        suggest = self.bot.get_channel(612530117830246400)
        em = discord.Embed(color=utils.random_color())
        em.title = f"{ctx.author} | User ID: {ctx.author.id}"
        em.description = idea
        try:
            i = ctx.guild.icon_url or self.bot.user.avatar_url
            em.set_footer(text=f"From {ctx.author.guild} | Server ID: {ctx.author.guild.id}",
                          icon_url=i)
        except:
            em.set_footer(text=f"Received from a Private channel.")
        await suggest.send(embed=em)
        await ctx.send("Your idea has been successfully sent to support server. Thank you!")

    @commands.command(aliases=["fan-art", "fan_art"])
    @commands.cooldown(1, 15, BucketType.user)
    async def fanart(self, ctx, *urls):
        """Submit an artwork made by you for this bot"""
        ch = self.bot.get_channel(612605556615806986)  # Fan-art channel

        # Set up the embed
        em = discord.Embed(title="Fan Art", description="New fan art submission")
        i = str(ctx.author.avatar_url) if ctx.author.avatar_url else self.bot.user.avatar_url
        em.set_author(name=ctx.author.name, icon_url=i)
        now = datetime.datetime.utcnow()
        em.set_footer(text=f"Artwork submitted on {now:%A, %B %d, %Y} at {now:%I:%M:%S %p} UTC.")

        # Get the media attachments of the accepted file types from the urls and attachments
        attachments: [discord.File] = []
        ex = [".jpg", ".png", ".gif", ".jpeg"]
        for url in urls:
            if not str(url).endswith(ex):
                await ctx.send(f"The given url {str(url)} does not point to a file with valid extension.\n"
                               f"The allowed extensions are: {str(ex)}")
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(url)) as resp:
                        content = io.BytesIO(await resp.content.read())
                        attachments.append(discord.File(content))
        for a in ctx.message.attachments:
            if str(a.filename).endswith(ex):
                attachments.append(a.to_file())
            else:
                await ctx.send(f"The attachment {str(a.filename)} does not point to a file with valid extension.\n"
                               f"The allowed extensions are: {str(ex)}")

        # Send it to the fan-arts submission channel if there are artworks attached else notify no artwork submitted
        if len(attachments) > 0:
            await ch.send(embed=em, files=attachments)
            for a in attachments:
                await utils.mysql_set(self.bot, id=ctx.author.name, arg1="fan_arts", arg2=a.url,
                                      arg3=now.strftime('%Y-%m-%d %H:%M:%S'))
            await ctx.send("The accepted extensions artworks are successfully sent to the support server.")
        else:
            await ctx.send("You did not give any valid media file url or attached a valid media file to your message.\n"
                           f"The allowed extensions are: {str(ex)}")

    @commands.group(invoke_without_command=True)
    async def math(self, ctx):
        """A command group for math commands"""
        # A command group containing commands for performing basic maths
        await ctx.send(
            'Available commands:\n`add <a> <b>`\n`subtract <a> <b>`\n`multiply <a> <b>`\n`divide <a> <b>`\n`remainder '
            '<a> <b>`\n`power <a> <b>`\n`factorial <a>`')

    @math.command(aliases=['*', 'x'])
    async def multiply(self, ctx, a: int, b: int):
        """Multiply two numbers"""
        em = discord.Embed(color=utils.random_color())
        em.title = "Result"
        em.description = f'❓ Problem: `{a}*{b}`\n✅ Solution: `{a * b}`'
        await ctx.send(embed=em)

    @math.command(aliases=['/', '÷'])
    async def divide(self, ctx, a: int, b: int):
        """Divide a number by a number"""
        try:
            em = discord.Embed(color=utils.random_color())
            em.title = "Result"
            em.description = f'❓ Problem: `{a}/{b}`\n✅ Solution: `{a / b}`'
            await ctx.send(embed=em)
        except ZeroDivisionError:
            em = discord.Embed(color=utils.random_color())
            em.title = "Error"
            em.description = "You can't divide by zero"
            await ctx.send(embed=em)

    @math.command(aliases=['+'])
    async def add(self, ctx, a: int, b: int):
        """Add a number to a number"""
        em = discord.Embed(color=utils.random_color())
        em.title = "Result"
        em.description = f'❓ Problem: `{a}+{b}`\n✅ Solution: `{a + b}`'
        await ctx.send(embed=em)

    @math.command(aliases=['-'])
    async def subtract(self, ctx, a: int, b: int):
        """Substract two numbers"""
        em = discord.Embed(color=utils.random_color())
        em.title = "Result"
        em.description = f'❓ Problem: `{a}-{b}`\n✅ Solution: `{a - b}`'
        await ctx.send(embed=em)

    @math.command(aliases=['%'])
    async def remainder(self, ctx, a: int, b: int):
        """Gets a remainder"""
        em = discord.Embed(color=utils.random_color())
        em.title = "Result"
        em.description = f'❓ Problem: `{a}%{b}`\n✅ Solution: `{a % b}`'
        await ctx.send(embed=em)

    @math.command(aliases=['^', '**'])
    async def power(self, ctx, a: int, b: int):
        """Raise A to the power of B"""
        if a > 100 or b > 100:
            return await ctx.send("Numbers are too large.")
        em = discord.Embed(color=utils.random_color())
        em.title = "Result"
        em.description = f'❓ Problem: `{a}^{b}`\n✅ Solution: `{a ** b}`'
        await ctx.send(embed=em)

    @math.command(aliases=['!'])
    async def factorial(self, ctx, a: int):
        """Factorial something"""
        if a > 813:
            await ctx.send("That number is too high to fit within the message limit for discord.")
        else:
            em = discord.Embed(color=utils.random_color())
            em.title = "Result"
            result = 1
            problem = a
            while a > 0:
                result = result * a
                a = a - 1
            em.description = f'❓ Problem: `{problem}!`\n✅ Solution: `{result}`'
            await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Utility(bot))
