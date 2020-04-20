import discord
from discord.ext import commands
from discord.ext.commands import BucketType
import datetime
import json
import io
import aiohttp
import pytz
import wikipedia
from ext import utils, paginator
from bot import MyBot
from typing import Any, Dict, List, Optional, AnyStr


class Utility(commands.Cog):
    """Useful and utility commands."""

    def __init__(self, bot: MyBot):
        self.bot: MyBot = bot

    @commands.group(aliases=["bombsquadmods", "bombsquad-mods", "mod-manager"], invoke_without_command=True)
    async def modmanager(self, ctx: commands.Context):
        """To search or list all the mods of BombSquad game in the mod manager."""
        await ctx.send(f"use this command as:\n"
                       f"i) `{ctx.prefix}{ctx.command} list` to get list of all.\n"
                       f"ii) `{ctx.prefix}{ctx.command} search <term>` to search for a term.")

    # noinspection DuplicatedCode
    @modmanager.command()
    async def list(self, ctx: commands.Context):
        """To list all mods of BombSquad game."""

        # Get the data of the current available to download mods
        repo: str = "Mrmaxmeier/BombSquad-Community-Mod-Manager"
        url: str = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data: Dict[str, Any] = json.loads(await resp.read())

        mods: Dict[str, Any] = data.get("mods", {})
        pages: List[discord.Embed] = []
        number: int = 0
        for mod in mods:
            # Add an embed page for each downloadable mod
            number += 1
            filename: Optional[str] = str(mods[mod].get("filename", None))
            em: discord.Embed = discord.Embed(title="Mods list of BombSquad Game",
                                              description=f"{number} numbered BombSquad game's mods in the ModManager.",
                                              color=utils.random_color())
            em.add_field(name=str(mod),
                         value=f"[Download Link](https://raw.githubusercontent.com/{repo}/master/mods/{filename})")
            pages.append(em)

        # Run the session
        p_session: paginator.PaginatorSession = paginator.PaginatorSession(ctx=ctx, timeout=120, pages=pages,
                                                                           color=utils.random_color(),
                                                                           footer="List of all BombSquad game's "
                                                                                  "mods in the ModManager.")
        await p_session.run()

    # noinspection DuplicatedCode
    @modmanager.command()
    async def search(self, ctx: commands.Context, *, search: str):
        """Search a mod in the BombSquad game's mod manager list."""

        # Get the downloadable mods
        repo: str = "Mrmaxmeier/BombSquad-Community-Mod-Manager"
        url: str = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data: Dict[str, Any] = json.loads(await resp.read())
        mods: Dict[str, Any] = data.get("mods", {})

        em: discord.Embed = discord.Embed(title=search, description=f"Search results for `{search}`.",
                                          color=utils.random_color())
        for mod in mods:
            if str(mod).lower().__contains__(search.lower()):
                # Loop through all mods and select the matching ones
                filename: Optional[str] = str(mods[mod].get("filename", None))
                em.add_field(name=str(mod),
                             value=f"[Download Link](https://raw.githubusercontent.com/{repo}/master/mods/{filename})")
        await ctx.send(embed=em)

    @commands.group(aliases=["accessoriesmanager", "accessories-manager"], invoke_without_command=True)
    async def accessories(self, ctx: commands.Context):
        """Search an accessory or list all accessories in my made BombSquad game's official accessories archive."""
        await ctx.send(f"use this command as:\n"
                       f"i) `{ctx.prefix}{ctx.command} list` to get list of all.\n"
                       f"ii) `{ctx.prefix}{ctx.command} search <term>` to search for a term.")

    # noinspection DuplicatedCode
    @accessories.command(name="list")
    async def _list(self, ctx: commands.Context):
        """To list all accessories of the BombSquad game."""

        # Get all available accessories
        repo: str = "BombSquaders/BombSquad-Official-Accessory-Archive"
        url: str = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data: Dict[str, Any] = json.loads(await resp.read())
        all_files: Dict[str, Any] = data.get("all-files", {})

        pages: List[discord.Embed] = []
        number: int = 0
        for accessory in all_files:
            # Add each accessory as an embed page
            number += 1
            filename: str = str(all_files[accessory].get("filename", None))
            author: str = str(all_files[accessory].get("author", None))
            name: str = str(all_files[accessory].get("name", None))
            em: discord.Embed = discord.Embed(title="Accessories list of BombSquad Game",
                                              description=f"{number} numbered BombSquad game's "
                                                          f"accessory in the AccessoriesArchive.",
                                              color=utils.random_color())
            em.add_field(name="Accessory Name", value=name)
            em.add_field(name="Author", value=author)

            # If accessory is single file give download link
            if not all_files[accessory].get("isCollection", False):
                em.add_field(name="Download Link",
                             value=f"https://raw.githubusercontent.com/{repo}/master/all-files/{filename}")

            # Else give the link to view it on Github
            else:
                rdir: str = str(all_files[accessory].get("rdir", None))
                em.add_field(name="Github Link", value=f"https://github.com/{repo}/tree/master/all-files/{rdir}")

            pages.append(em)
        p_session: paginator.PaginatorSession = paginator.PaginatorSession(ctx=ctx, timeout=120, pages=pages,
                                                                           color=utils.random_color(),
                                                                           footer="List of all BombSquad game's "
                                                                                  "accessory in the AccessoryArchive.")
        await p_session.run()

    # noinspection DuplicatedCode
    @accessories.command(name="search")
    async def _search(self, ctx: commands.Context, *, search: str):
        """To search for an accessory in the list of all accessories."""

        # Get available accessories
        repo: str = "BombSquaders/BombSquad-Official-Accessory-Archive"
        url: str = f"https://raw.githubusercontent.com/{repo}/master/index.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data: Dict[str, Any] = json.loads(await resp.read())
        all_files: Dict[str, Any] = data.get("all-files", {})

        # Add only those accessories that matches the search term
        em: discord.Embed = discord.Embed(title=search, description=f"Search results for `{search}`.",
                                          color=utils.random_color())
        for accessory in all_files:
            if str(accessory).lower().__contains__(search.lower()):
                filename: str = str(all_files[accessory].get("filename", None))
                author: str = str(all_files[accessory].get("author", None))
                name: str = str(all_files[accessory].get("name", None))
                if not all_files[accessory].get("isCollection", False):
                    em.add_field(name=name,
                                 value=f"Author: {author}\n[Download Link](https://raw.githubusercontent.com/{repo}"
                                       f"/master/all-files/{filename})")
                else:
                    rdir: str = str(all_files[accessory].get("rdir", None))
                    em.add_field(name=name,
                                 value=f"Author: {author}\n[Github Link](https://github.com/{repo}/tree/master/all-"
                                       f"files/{rdir})")
        await ctx.send(embed=em)

    @commands.command()
    async def datetime(self, ctx: commands.Context, *, tz: Optional[str] = None):
        """Get the current date and time for a time zone or UTC."""

        # Send the current datetime
        now: datetime
        now = datetime.datetime.now(tz=pytz.UTC)
        if tz:
            try:
                now = now.astimezone(pytz.timezone(tz))
            except Exception:
                em: discord.Embed = discord.Embed(color=utils.random_color())
                em.title = "Invalid timezone"
                em.description = f'Please search for the list of timezones on google.'
                return await ctx.send(embed=em)
        await ctx.send(f'It is currently {now:%A, %B %d, %Y} at {now:%I:%M:%S %p}.')

    @commands.command(aliases=['wikipedia'])
    async def wiki(self, ctx: commands.Context, *, query: str):
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
    async def feedback(self, ctx: commands.Context, *, idea: str):
        """Suggest an idea, or complain an issue."""
        suggest: discord.TextChannel = self.bot.get_channel(612530117830246400)
        em = discord.Embed(color=utils.random_color())
        em.title = f"{ctx.author} | User ID: {ctx.author.id}"
        em.description = idea
        try:
            i = ctx.guild.icon_url or self.bot.user.avatar_url
            em.set_footer(text=f"From {ctx.author.guild} | Server ID: {ctx.author.guild.id}",
                          icon_url=i)
        except Exception:
            em.set_footer(text=f"Received from a Private channel.")
        await suggest.send(embed=em)
        await ctx.send("Your idea has been successfully sent to support server. Thank you!")

    @commands.command(aliases=["bs_servers_list", "bs-servers-list"])
    @commands.cooldown(1, 15, BucketType.user)
    async def _bs_search(self, ctx: commands.Context, *, region: str):
        """To get a list of servers according to region."""
        # Made By: AwesomeLogic
        url: str = f"https://awesomelogic.herokuapp.com/api/{region}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data: List[Dict[AnyStr, Any]] = json.loads(await resp.read())
        except Exception:
            em = discord.Embed(title=f'{region} is not in Region List.', color=utils.random_color())
            async with aiohttp.ClientSession() as session:
                async with session.get('https://awesomelogic.herokuapp.com/api/regions') as resp:
                    data: Dict[str, Any] = json.loads(await resp.read())
            em.add_field(name='Available Regions',
                         value=str(data))
            await ctx.send(embed=em)
            return

        em = discord.Embed(title=f'BS Server List in {region}', description="Credits: AwesomeLogic",
                           color=utils.random_color())
        for i in data:
            name = str(i['name'])
            ip = str(i['ip'])
            port = str(i['port'])
            full = str(i['full'])
            em.add_field(name=name,
                         value=f"IP: {ip}\nPort: {port}\nParty is Full:{full}")
        await ctx.send(embed=em)

    @commands.command(aliases=["fan-art", "fan_art"])
    @commands.cooldown(1, 15, BucketType.user)
    async def fanart(self, ctx: commands.Context, *urls: List[str]):
        """Submit an artwork made by you for this bot"""
        ch: discord.TextChannel = self.bot.get_channel(612605556615806986)  # Fan-art channel

        # Set up the embed
        em: discord.Embed = discord.Embed(title="Fan Art", description="New fan art submission")
        i: str = str(ctx.author.avatar_url) if ctx.author.avatar_url else self.bot.user.avatar_url
        em.set_author(name=ctx.author.name, icon_url=i)
        now: datetime = datetime.datetime.utcnow()
        em.set_footer(text=f"Artwork submitted on {now:%A, %B %d, %Y} at {now:%I:%M:%S %p} UTC.")

        # Get the media attachments of the accepted file types from the urls and attachments
        attachments: List[discord.File] = []
        ex = (".jpg", ".png", ".gif", ".jpeg")
        for url in urls:
            if not str(url).endswith(ex):
                await ctx.send(f"The given url {str(url)} does not point to a file with valid extension.\n"
                               f"The allowed extensions are: {str(ex)}")
            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(str(url)) as resp:
                        content = io.BytesIO(await resp.content.read())
                        attachments.append(
                            discord.File(content, filename=str(url).split("/")[-1]))
        a: discord.Attachment
        for a in ctx.message.attachments:
            if str(a.filename).endswith(ex):
                attachments.append(await a.to_file())
            else:
                await ctx.send(f"The attachment {str(a.filename)} does not point to a file with valid extension.\n"
                               f"The allowed extensions are: {str(ex)}")

        # Send it to the fan-arts submission channel if there are artworks attached else notify no artwork submitted
        if len(attachments) > 0:
            msg = await ch.send(embed=em, files=attachments)
            for a in msg.attachments:
                await utils.mysql_set(self.bot, id=str(ctx.author.name), arg1="fan_arts", arg2=a.url,
                                      arg3=now.strftime('%Y-%m-%d %H:%M:%S'))
            await ctx.send("The accepted extensions artworks are successfully sent to the support server.")
        else:
            await ctx.send("You did not give any valid media file url or attached a valid media file to your message.\n"
                           f"The allowed extensions are: {str(ex)}")


def setup(bot: MyBot):
    bot.add_cog(Utility(bot))
