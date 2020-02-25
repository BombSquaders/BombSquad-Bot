import aiohttp
import asyncio
import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw
from io import BytesIO
from ext.utils import mysql_set, get_user_data
from ext.paginator import PaginatorSession
import mysql.connector
import datetime
import json
import os
import random


def get_random_events(bot, server_id: str) -> list:
    """A synchronous method to get random events allowed or not to be used in the synchronous check function."""

    def to_run():
        bot.MySQLConnection.cmd_refresh(1)
        bot.MySQLCursor.execute(f"SELECT * FROM `servers` WHERE id={server_id};")
        data = bot.MySQLCursor.fetchall()

        if len(data) == 0:
            return False

        return int(data[0][5]) == 1

    try:
        return to_run()
    except mysql.connector.errors.ProgrammingError:
        bot.MySQLConnection = mysql.connector.connect(host='localhost',
                                                      database=os.environ.get("mysql_database"),
                                                      user=os.environ.get("mysql_user"),
                                                      password=os.environ.get("mysql_password"))
        bot.MySQLCursor = bot.MySQLConnection.cursor()
        return to_run()


async def get_user_avatar(user: discord.Member) -> bytes:
    # Get the user avatar url in png format
    avatar_url = str(user.avatar_url_as(format="png", size=512))

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            # Get the bytes of the image
            avatar_bytes = await response.read()

    return avatar_bytes


class Currency(commands.Cog):
    """Customize your server with these config commands."""
    fighting: list = []

    def __init__(self, bot):
        self.bot = bot
        self.bg_images_location = os.path.join(bot.basedir, "data/card-bg-images")
        self.bg_images: list = [str(x) for x in os.listdir(self.bg_images_location) if str(x).endswith(".jpg")]
        self.bg_images.sort()
        self.base_bg_images_url = "https://static.bombsquadbot.tk/card-custom-bg-images/"
        self.random_events.start()

    def cog_unload(self):
        self.random_events.cancel()

    # Run a random event every 5 minutes in a random server
    @tasks.loop(minutes=5)
    async def random_events(self):
        # Check if it is a valid guild channel which has random events enabled
        def pred(msg: discord.Message):
            nonlocal self
            is_valid_guild_text_channel = not (
                    isinstance(msg.channel, discord.DMChannel) or isinstance(msg.channel,
                                                                             discord.GroupChannel)) and isinstance(
                msg.channel, discord.TextChannel)
            if not is_valid_guild_text_channel:
                return False
            random_events_allowed = get_random_events(self.bot, msg.guild.id)
            guild: discord.Guild = msg.guild
            channel: discord.TextChannel = msg.channel
            perms: discord.Permissions = channel.permissions_for(discord.utils.get(guild.members, id=self.bot.user.id))
            p_allowed = perms.send_messages and perms.use_external_emojis and perms.read_messages
            return random_events_allowed and p_allowed

        # Wait for a message by anyone in any guild else run after another 30 minutes
        try:
            m: discord.Message = await self.bot.wait_for('message', check=pred)
        except Exception as e:
            # Print any exception and return, do not let any exception raise else the loop will terminate
            print(e)
            return

        # Start a random event in the channel from where we received a message
        r = random.randint(1, 25)
        if r == 25:
            title = "A legendary event occurred"
            timeout = 15
            color = discord.Color.dark_orange()
            events = self.bot.r_events["legendary"]
        elif r > 20:
            timeout = 20
            title = "An epic event occurred"
            color = discord.Color.blurple()
            events = self.bot.r_events["epic"]
        elif r > 10:
            timeout = 30
            title = "A rare event occurred"
            color = discord.Color.blue()
            events = self.bot.r_events["rare"]
        else:
            timeout = 60
            title = "A common event occurred"
            color = discord.Color.green()
            events = self.bot.r_events["common"]

        event = events[random.choice([x for x in events.keys()])]
        wait_for = event["wait_for"]
        em: discord.Embed = discord.Embed(title=title, description=event["description"], color=color)
        em.add_field(name="The first user to", value=event["value"], inline=False)
        m = await m.channel.send(embed=em)
        print(wait_for)
        if wait_for == "reaction_add":
            await m.add_reaction(str(event["answer"]))
        await asyncio.sleep(0.01)

        def pred(*args):
            nonlocal m, wait_for
            tr = False
            if wait_for == "message":
                msg: discord.Message = args[0]
                tr = msg.channel.id == m.channel.id and str(msg.content).lower().__contains__(
                    str(event["answer"]).lower()) and not msg.author.bot
            elif wait_for == "reaction_add":
                react: discord.Reaction = args[0]
                u: discord.User = args[1]
                tr = react.message.id == m.id and str(react.emoji) == str(event["answer"]) and not u.bot
            print(tr)
            return tr

        try:
            if wait_for == "message":
                message: discord.Message = await self.bot.wait_for('message', check=pred, timeout=timeout)
                user = message.author
            elif wait_for == "reaction_add":
                reaction, user = await self.bot.wait_for('reaction_add', check=pred, timeout=timeout)
            else:
                print("Unknown wait_for: " + wait_for)
                return
        except asyncio.TimeoutError:
            return await m.channel.send("The event expired, you all are lazy.")
        except Exception as e:
            print(e)  # If there is any other error from network, print it to the console and return to let the loop run
            return

        for r in m.reactions:
            for us in r.users():
                await m.remove_reaction(r.emoji, us)

        gloves = "boxing_gloves"
        power = [x for x in self.bot.purchasables.keys() if str(x) != gloves and str(x) != "bombs"]
        powers = {}
        data = await get_user_data(self.bot, user)
        now = datetime.datetime.utcnow()
        to_grant: str = event["grant"]["name"]
        grant_amount: int = event["grant"]["amount"]
        if to_grant in power:
            for key in data[3].keys():
                k_item = data[3][key]
                if not datetime.datetime.strptime(k_item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                    if str(key) == to_grant:
                        expire = now + datetime.timedelta(days=2)
                        k_item["count"] = int(int(k_item["count"]) + int(grant_amount))
                        k_item["expires"] = f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"
                    powers[key] = k_item
            if to_grant not in powers.keys():
                value = {}
                expire = now + datetime.timedelta(days=2, hours=12)
                value["count"] = int(grant_amount)
                value["expires"] = f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"
                powers[to_grant] = value
            await mysql_set(self.bot, user.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(powers))}'")
        elif to_grant == gloves:
            for key in data[3].keys():
                value = data[3][key]
                if not datetime.datetime.strptime(value["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                    powers[key] = value
            expire = now + datetime.timedelta(days=2, hours=12)
            powers[gloves] = {"count": 1, "expires": f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"}
            await mysql_set(self.bot, user.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(powers))}'")
        else:
            if to_grant == "tickets":
                amount = grant_amount + data[1]
            elif to_grant == "bombs":
                amount = grant_amount + data[2]
            else:
                return print("Invalid grant item: " + to_grant)
            await mysql_set(self.bot, user.id, arg1="players", arg2=to_grant, arg3=f"{str(amount)}")

        await m.channel.send(f"{user.mention}, you have successfully won {grant_amount} {to_grant}")

    @random_events.before_loop
    async def before_random_events(self):
        # Wait until bot ready and a few more time before starting the loop
        await self.bot.wait_until_ready()
        await asyncio.sleep(0.075)

    @random_events.after_loop
    async def after_random_events(self):
        # Random events loop has been terminated due to cog unload or an exception
        pass

    async def get_user_image(self, user: discord.Member) -> BytesIO:
        """Returns BytesIO of an image set up with a background and the user avatar on it."""
        data = await get_user_data(self.bot, user)

        # The user avatar image
        with Image.open(BytesIO(await get_user_avatar(user))) as im:
            # The background image
            with Image.open(os.path.join(self.bg_images_location, data[4])) as background:
                # This ensures that the user's avatar lacks an alpha channel,
                # as we're going to be substituting our own here.
                rgb_avatar = im.convert("RGB")

                # This is the mask image we will be using to create the circle cutout effect on the avatar.
                with Image.new("L", im.size) as mask:
                    # ImageDraw lets us draw on the image, in this instance,
                    # we will be using it to draw a white circle on the mask image.
                    mask_draw = ImageDraw.Draw(mask)

                    # Draw the white circle from 0, 0 to the bottom right corner of the image
                    mask_draw.ellipse([(0, 0), im.size], fill=255)

                    # Paste the alpha-less avatar on the background using the new circle mask we just created.
                    background.paste(rgb_avatar, (0, 0), mask=mask)

                # Prepare the stream to save this image into
                final_buffer = BytesIO()

                # Save into the stream, using png format.
                background.save(final_buffer, "png")

        # Seek back to the start of the stream
        final_buffer.seek(0)

        # Return the prepared stream
        return final_buffer

    @commands.command(aliases=["player", "flex", "profile"])
    async def player_stats(self, ctx, user: discord.User = None):
        """To get your info in the Bot's game"""
        if user is None:
            user = ctx.author
        user_stats = await get_user_data(self.bot, user)

        # Return with sending a warning if the user is dead
        dead = user_stats[5]
        if dead is not None:
            dead_time = datetime.datetime.utcnow() - dead
            if dead_time < datetime.timedelta(minutes=1, seconds=30):
                return await ctx.send(f"{user.mention}, You cannot use this command when dead.")
            await mysql_set(self.bot, user.id, arg1="players", arg2="dead", arg3='NULL')

        final_buffer = await self.get_user_image(user)  # Get the bytes of the image to send

        # Now, prepare the image file to send with the embed containing the information
        file = discord.File(filename=f"{user.name}.png", fp=final_buffer)
        em = discord.Embed(title="Player stats", description="Following are your stats.")
        em.add_field(name="Tickets", value=str(user_stats[1]))
        em.add_field(name="Bombs", value=str(user_stats[2]))

        # Make a copy of the powers available to the user to modify it in future without changing the iterable
        powers_json: dict = json.loads(str(json.dumps(user_stats[3])))
        powers = ""
        if len(user_stats[3]) == 0:
            powers = "None"
        for key in user_stats[3].keys():
            item = user_stats[3][key]
            if datetime.datetime.strptime(item["expires"], '%Y-%m-%d %H:%M:%S') <= datetime.datetime.utcnow():
                powers_json.pop(key)
            else:
                powers += f"**{str(item['count']) + ' ' + key}** - _Expires on:_ `{item['expires']}`\n"

        if len(powers_json) != len(user_stats[3]):  # If modified save the powers
            await mysql_set(self.bot, user.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(powers_json))}'")

        em.add_field(name="Powers", value=powers, inline=False)

        # Send it
        await ctx.send(file=file, embed=em)

    @commands.command(aliases=["purchase"])
    async def store(self, ctx, power: str = None, amount: int = 1):
        """To view or purchase a powerup for yourself."""
        # The valid purchasable items
        items = [x for x in self.bot.purchasables.keys()]
        s_help = f"The powerup {power} does not exist.\n" \
                 f"Following are the valid items, each expire after 2 and a half days except normal bombs:\n"
        for i in range(len(items)):
            item = self.bot.purchasables[items[i]]
            s_help += f"{int(i) + 1}) `{items[i]}` {item['description']}\n"

        if power is None or power not in items:
            return await ctx.send(s_help)

        # Can not use command while fighting
        if ctx.author.id in self.fighting:
            return await ctx.send("You can not use this command while in battle")

        # Get the current data of the user
        data = await get_user_data(self.bot, ctx.author)

        # Return with sending a warning if the user is dead
        dead = data[5]
        if dead is not None:
            dead_time = datetime.datetime.utcnow() - dead
            if dead_time < datetime.timedelta(minutes=1, seconds=30):
                return await ctx.send(f"{ctx.author.mention}, You cannot use this command when dead.")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="dead", arg3='NULL')

        gloves = "boxing_gloves"
        n_bombs = "bombs"

        # Set the cost and amount of the purchase
        if power == gloves:
            amount = 1
        cost = int(self.bot.purchasables[power]["cost"]) * amount

        # If user has enough tickets then continue else return warning
        if int(data[1]) < cost:
            return await ctx.send(f"You do not have enough credit for the {amount} {power}, it costs {str(cost)}")

        powers: dict = {}  # A dict to store the latest powerup data in
        now = datetime.datetime.utcnow()
        for key in data[3].keys():
            item = data[3][key]
            if not datetime.datetime.strptime(item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                if str(key) == power:
                    expire = now + datetime.timedelta(days=2)
                    item["count"] = int(int(item["count"]) + amount) if power != gloves else 1
                    item["expires"] = f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"
                powers[key] = item

        # Make sure the powerup is in the dict
        if power not in powers.keys() and power != n_bombs:
            value = {}
            expire = now + datetime.timedelta(days=2, hours=12)
            value["count"] = int(amount)
            value["expires"] = f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"
            powers[power] = value

        # At last, deduct the tickets and increment the purchased item
        if power == n_bombs:
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="bombs",
                            arg3=f'"{str(int(data[2]) + amount)}"')
        else:
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(powers))}'")
        await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="tickets",
                        arg3=f'{str(int(data[1]) - int(cost))}')
        return await ctx.send(f"Successfully purchased {amount} {power}.")

    @commands.group(invoke_without_command=True, aliases=["card_bg", "custom_bg"])
    async def card_background(self, ctx):
        """To show all/one background for your card or set one."""

        await ctx.send("Following are the sub commands to use this commands group:\n"
                       "1) `show [number]` this command can be used to show all available custom card backgrounds or"
                       " any specific card background by providing the index of the background to view.\n"
                       "2) `set <number>` to set the custom card background to the given number,"
                       " costs 50 tickets.")

    @card_background.command()
    async def show(self, ctx, number: int = None):
        """To show all or chosen one custom background image for your card."""
        # Get the current data of the user
        data = await get_user_data(self.bot, ctx.author)

        # Return with sending a warning if the user is dead
        dead = data[5]
        if dead is not None:
            dead_time = datetime.datetime.utcnow() - dead
            if dead_time < datetime.timedelta(minutes=1, seconds=30):
                return await ctx.send(f"{ctx.author.mention}, You cannot use this command when dead.")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="dead", arg3='NULL')

        if number is None:

            # The pages to be shown in paginator session
            pages = []

            # Add all available custom_bg images
            index = 0
            for image in self.bg_images:
                index += 1
                em = discord.Embed(title=f"Custom card background number `{str(index)}`", description=str(image))
                em.set_image(url=self.base_bg_images_url + str(image))
                pages.append(em)

            # Instantiate and run the paginator session
            p_session = PaginatorSession(ctx, footer=f'Use `{ctx.prefix}card_bg set <number>` set a bg', pages=pages)
            return await p_session.run()
        else:
            try:
                image = self.bg_images[number - 1]
                em = discord.Embed(title=f"Custom card background number `{str(number)}`", description=str(image))
                em.set_image(url=self.base_bg_images_url + str(image))
                return await ctx.send(embed=em)
            except IndexError:
                return await ctx.send("Any background image does not exists at the number.")

    @card_background.command()
    async def set(self, ctx, number: int):
        """To set a custom background image for your card."""
        # Can not use command while fighting
        if ctx.author.id in self.fighting:
            return await ctx.send("You can not use this command while in battle")

        # Get the current data of the user
        data = await get_user_data(self.bot, ctx.author)

        # Return with sending a warning if the user is dead
        dead = data[5]
        if dead is not None:
            dead_time = datetime.datetime.utcnow() - dead
            if dead_time < datetime.timedelta(minutes=1, seconds=30):
                return await ctx.send(f"{ctx.author.mention}, You cannot use this command when dead.")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="dead", arg3='NULL')

        try:
            image = self.bg_images[number - 1]
            data = await get_user_data(self.bot, ctx.author)

            # If user has enough tickets then continue else return warning
            if int(data[1]) < 50:
                return await ctx.send("You do not have enough credit for changing card background, it cost 35")

            # Deduct the credits and set the background
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="custom_bg", arg3=f"'{image}'")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="tickets", arg3=f'{str(int(data[1]) - 50)}')

            return await ctx.send("Successfully updated the background.")
        except IndexError:
            return await ctx.send("Any background image does not exists at the number.")


def setup(bot):
    bot.add_cog(Currency(bot))
