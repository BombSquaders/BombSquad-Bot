import aiohttp
import asyncio
import discord
from discord.ext import commands, tasks
from PIL import Image, ImageDraw
from io import BytesIO
from ext.utils import mysql_set, get_user_data, get_user_vote, increment_ticket
from ext.paginator import PaginatorSession
from collections import OrderedDict
import datetime
import json
import os
import random


async def get_user_avatar(user: discord.Member) -> bytes:
    # Get the user avatar url in png format
    avatar_url = str(user.avatar_url_as(format="png", size=512))

    async with aiohttp.ClientSession() as session:
        async with session.get(avatar_url) as response:
            # Get the bytes of the image
            avatar_bytes = await response.read()

    return avatar_bytes


class UsersFight(object):
    """To engage user(s) in fight."""

    def __init__(self, ctx, challenger: discord.User, challenged: discord.User, timeout=60,
                 color=discord.Color.green(), footer=''):
        self.footer: str = footer  # Footer message
        self.bot = ctx.bot  # The bot
        self.user: discord.User = challenger  # Who started fight
        self.enemy: discord.User = challenged  # Who is challenged
        self.powers: dict = {}  # The powers the users have, will be set later because requires await
        self.fighters: dict = {
            "healths": {
                str(challenger.id): 100,
                str(challenged.id): 100
            },
            "frozen": {
                str(challenger.id): None,
                str(challenged.id): None
            }
        }  # The healths of the users, and some effects on the users
        self.current: discord.User = challenger  # The current turn user
        self.timeout: float = timeout  # When to end the fight after inactivity
        self.running: bool = False  # Currently running, bool
        self.messagable: discord.abc.Messageable = ctx  # Where to send fight messages
        self.message: discord.Message = None  # The message with fight details
        self.color: discord.Colour = color  # Embed color
        self.reactions = OrderedDict({
            '<:buttonPunch:680740252247130113>': self.punch,
            '<:buttonBomb:680740236896108573>': self.bomb,
            '<:IceBomb:680740264138113025>': self.ice_bomb,
            '<:StickyBomb:680740249105596418>': self.sticky_bomb,
            '<:AutoAimBomb:681141263033958423>': self.auto_aim_bomb
        })

    async def get_fight_image(self) -> BytesIO:
        """Returns BytesIO of an image set up with a background and the user avatar on it."""
        # Fight image
        with Image.open(os.path.join(self.bot.basedir, "data/versus.png")) as background:
            with Image.open(BytesIO(await get_user_avatar(self.user))) as challenger:
                # This ensures that the user's avatar lacks an alpha channel,
                # as we're going to be substituting our own here.
                rgb_avatar = challenger.convert("RGB")

                # This is the mask image we will be using to create the circle cutout effect on the avatar.
                with Image.new("L", challenger.size) as mask:
                    # ImageDraw lets us draw on the image, in this instance,
                    # we will be using it to draw a white circle on the mask image.
                    mask_draw = ImageDraw.Draw(mask)

                    # Draw the white circle from 0, 0 to the bottom right corner of the image
                    mask_draw.ellipse([(0, 0), challenger.size], fill=255)

                    # Paste the alpha-less avatar on the background using the new circle mask we just created.
                    background.paste(rgb_avatar, (0, 0), mask=mask)

            with Image.open(BytesIO(await get_user_avatar(self.enemy))) as challenged:
                # This ensures that the user's avatar lacks an alpha channel,
                # as we're going to be substituting our own here.
                rgb_avatar = challenged.convert("RGB")

                # This is the mask image we will be using to create the circle cutout effect on the avatar.
                with Image.new("L", challenged.size) as mask:
                    # ImageDraw lets us draw on the image, in this instance,
                    # we will be using it to draw a white circle on the mask image.
                    mask_draw = ImageDraw.Draw(mask)

                    # Draw the white circle from 0, 0 to the bottom right corner of the image
                    mask_draw.ellipse([(0, 0), challenged.size], fill=255)

                    # Paste the alpha-less avatar on the background using the new circle mask we just created.
                    background.paste(rgb_avatar, (1536, 0), mask=mask)

            # Prepare the stream to save this image into
            final_buffer = BytesIO()

            # Save into the stream, using png format.
            background.save(final_buffer, "png")

        # Seek back to the start of the stream
        final_buffer.seek(0)

        # Return the prepared stream
        return final_buffer

    # noinspection PyUnusedLocal
    def react_check(self, reaction, user) -> bool:
        """Check to make sure it only responds to reactions from the current user and on the same message."""
        return reaction.message.id == self.message.id

    async def run(self):
        """Actually runs the fighting session"""
        if not self.running:
            # set the powers the fighters have at the time of fight start
            d1 = await get_user_data(self.bot, self.user.id)
            d2 = await get_user_data(self.bot, self.enemy.id)
            now = datetime.datetime.utcnow()

            p1: dict = {}
            p2: dict = {}
            for key in self.bot.purchasables.keys():
                p1[str(key)] = {"count": 0, "available": False}
                p2[str(key)] = {"count": 0, "available": False}

            for key in d1[3].keys():
                item = d1[3][key]
                if not datetime.datetime.strptime(item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                    p1[key] = {
                        "count": item["count"],
                        "available": True
                    }
            for key in d2[3].keys():
                item = d2[3][key]
                if not datetime.datetime.strptime(item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                    p2[key] = {
                        "count": item["count"],
                        "available": True
                    }

            self.fighters["powers"] = {
                str(self.user.id): {
                    "gloves": p1["boxing_gloves"]["available"],
                    "bombs": int(d1[2]),
                    "ice_bombs": p1["ice_bombs"]["count"],
                    "sticky_bombs": p1["sticky_bombs"]["count"],
                    "auto_aim_bombs": p1["auto_aim_bombs"]["count"]
                },
                str(self.enemy.id): {
                    "gloves": p2["boxing_gloves"]["available"],
                    "bombs": int(d2[2]),
                    "ice_bombs": p2["ice_bombs"]["count"],
                    "sticky_bombs": p2["sticky_bombs"]["count"],
                    "auto_aim_bombs": p2["auto_aim_bombs"]["count"]
                }
            }

            # Prepare the image file and send with the message embed
            # Using css formatting in description to add colours and look like blocks
            em = discord.Embed(title=f"{self.user.name} versus {self.enemy.name}",
                               description="```css\n...\n...\n...\n...\n...\n...\nMatch Started\n```")
            em.add_field(name="Current turn", value=self.current.mention, inline=False)
            em.add_field(name=self.user.name, value="100 hp")
            em.add_field(name=self.enemy.name, value="100 hp")
            final_buffer = await self.get_fight_image()
            self.message = await self.messagable.send(
                file=discord.File(filename=f"{self.user.name} versus {self.enemy.name}.png", fp=final_buffer),
                embed=em)

            # add the reactions
            for r in self.reactions.keys():
                await self.message.add_reaction(r)
                await asyncio.sleep(0.05)  # just to make sure the reactions get added without being rate limited

            # starts the fight session if not yet fighting
            Currency.fighting.append(self.user.id)
            Currency.fighting.append(self.enemy.id)
            Currency.fighting.append(self.message.guild.id)
            self.running = True
            await self.messagable.send(f"Use the reactions below the pvp embed message to fight.\n"
                                       f"It is currently your turn {self.user.mention}, be ready {self.enemy.mention}")

        while self.running:
            try:
                # waits for reaction using react_check
                reaction, user = await self.bot.wait_for('reaction_add', check=self.react_check, timeout=self.timeout)
            except asyncio.TimeoutError:
                self.running = False
                try:
                    await self.message.clear_reactions()  # tries to remove reactions
                except:
                    pass  # no perms
                finally:
                    await self.over()
            else:
                try:
                    # remove all added reactions
                    await self.message.remove_reaction(reaction, user)
                except Exception as e:
                    await self.messagable.send("Unable to remove reactions due to error: " + str(type(e)))

                # process the wanted reactions
                if user.id == self.current.id and str(reaction.emoji) in self.reactions.keys():
                    action = self.reactions[str(reaction.emoji)]  # gets the function from the reaction map OrderedDict
                    await action()  # awaits here with () because __init__ can't be async
                    await asyncio.sleep(0.25)  # wait here for small time to avoid pass the message editing rate-limits

    # All functions with await must be async

    async def change_current(self, enemy: discord.User, o: discord.Embed):
        self.current = enemy
        em = discord.Embed(title=o.title, description=o.description)
        em.add_field(name="Current turn", value=self.current.mention, inline=False)
        em.add_field(name=self.user.name, value=self.fighters['healths'][str(self.user.id)])
        em.add_field(name=self.enemy.name, value=self.fighters['healths'][str(self.enemy.id)])
        await self.message.edit(embed=em)

    async def damage(self, user: discord.User, hit: float, o: discord.Embed = None) -> str:
        if not o:
            o = self.message.embeds[0]
            o.description = "```css\n" + o.description.lstrip("```css\n").rstrip("```").split("\n", 1)[1]

        # deduct the health, but do not let it drop below 0
        d: datetime.datetime = self.fighters["frozen"][str(user.id)]
        if d is not None and (d + datetime.timedelta(seconds=10)) >= datetime.datetime.utcnow():
            hit *= 1.25
        else:
            self.fighters["frozen"][str(user.id)] = None
        hit = round(hit, 2)
        n = self.fighters["healths"][str(user.id)] - hit
        self.fighters["healths"][str(user.id)] = n if not n < 0 else 0

        n = o.description + f"{user.name} lost {hit} hp\n"

        # end match if dead
        if not self.fighters["healths"][str(user.id)] > 0:
            winner: discord.User = self.enemy if user.id == self.user.id else self.user
            # prepare the new embed for the message
            em = discord.Embed(title=o.title, description=n + f"{user.name} died!\n```")
            em.add_field(name=self.user.name, value=self.fighters['healths'][str(self.user.id)])
            em.add_field(name=self.enemy.name, value=self.fighters['healths'][str(self.enemy.id)])
            await self.message.edit(embed=em)
            await self.over(reason=f"{winner.mention} has won the match!")
            await self.messagable.send(
                f"{user.mention}, now you are dead and can't use game commands for one and a half minute.")
            await mysql_set(self.bot, user.id, arg1="players", arg2="dead",
                            arg3=f"'{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}'")
            return None

        return n

    async def punch(self):
        # the current attacker and enemy
        attacker: discord.User = self.current
        enemy: discord.User = self.enemy if self.current.id == self.user.id else self.user

        # add notification about using punch
        em: discord.Embed = self.message.embeds[0]
        em.description = "```css\n" + em.description.lstrip("```css\n").rstrip("```").split("\n", 3)[
            3] + f"{attacker.name} used punch on {enemy.name}\n"

        # generate base damage with some randomness
        base_hit_damage: float = round(12.50 * random.uniform(0.95, 1.00), 2)
        if self.fighters["powers"][str(attacker.id)]["gloves"]:
            base_hit_damage += 2.5

        # get the random action
        events = ["self", "missed", "hit", "critical"]
        action = random.choice(events)

        if action != "self":
            if action == "missed":
                em.description += f"{enemy.name} dodged the punch\n"
                n = await self.damage(enemy, 0, o=em)
                if not n:
                    return
                em.description = n
            elif action == "hit":
                em = self.message.embeds[0]
                em.description += f"{enemy.name} was hit by the punch\n`"
                n = await self.damage(enemy, base_hit_damage, o=em)
                if not n:
                    return
                em.description = n
            elif action == "critical":
                em = self.message.embeds[0]
                em.description += f"{enemy.name} had a critical hit!!\n"
                n = await self.damage(enemy, base_hit_damage + 2.5, o=em)
                if not n:
                    return
                em.description = n
        else:
            em = self.message.embeds[0]
            em.description += f"{attacker.name} missed and punched himself!\n"
            await self.message.edit(embed=em)
            n = await self.damage(attacker, base_hit_damage, o=em)
            if not n:
                return
            em.description = n

        em.description += "```"
        await self.change_current(enemy, o=em)

    async def bomb(self, b=1):
        # the current attacker and enemy
        attacker: discord.User = self.current
        enemy: discord.User = self.enemy if self.current.id == self.user.id else self.user

        em: discord.Embed = self.message.embeds[0]

        async def n_bomb_check(e: discord.Embed):
            nonlocal b

            # generate base damage with some randomness
            bhd: float = round(15.50 * random.uniform(0.95, 1.00), 2)

            bo = "normal bomb"

            if b == 2:
                bo = "ice bomb"
                bhd -= 1.5
                count = int(self.fighters["powers"][str(attacker.id)]["ice_bombs"])
                if count <= 0:
                    e.description = "```css" + em.description.lstrip("```css\n").rstrip("```").split("\n", 1)[
                        1] + f"{attacker.name} you do not have any {bo}, continued to default bomb\n"
                    b = 1
                    return await n_bomb_check(e)
                else:
                    self.fighters["powers"][str(attacker.id)]["ice_bombs"] = count - 1
            elif b == 3:
                bo = "sticky bomb"
                count = int(self.fighters["powers"][str(attacker.id)]["sticky_bombs"])
                if count <= 0:
                    e.description = "```css" + em.description.lstrip("```css\n").rstrip("```").split("\n", 1)[
                        1] + f"{attacker.name} you do not have any {bo}, continuing to default bomb\n"
                    b = 1
                    return await n_bomb_check(e)
                else:
                    self.fighters["powers"][str(attacker.id)]["sticky_bombs"] = count - 1
            elif b == 4:
                bo = "auto aim bomb"
                count = int(self.fighters["powers"][str(attacker.id)]["auto_aim_bombs"])
                if count <= 0:
                    e.description = "```css" + em.description.lstrip("```css\n").rstrip("```").split("\n", 1)[
                        1] + f"{attacker.name} you do not have any {bo}, continuing to default bomb\n"
                    b = 1
                    return await n_bomb_check(e)
                else:
                    self.fighters["powers"][str(attacker.id)]["auto_aim_bombs"] = count - 1
            else:
                count = int(self.fighters["powers"][str(attacker.id)]["bombs"])
                if count <= 0:
                    e.description = "```css" + em.description.lstrip(
                        "```css\n").rstrip("```").split("\n", 1)[
                        1] + f"{attacker.name} you do not have any normal bomb, please use a " \
                             f"different attack option\n```"
                    await self.message.edit(embed=e)
                    return await self.messagable.send(
                        f"{attacker.mention}, you do not have any normal bomb, please use other options")
                else:
                    self.fighters["powers"][str(attacker.id)]["bombs"] = count - 1
            return bo, bhd

        try:
            bomb, base_hit_damage = await n_bomb_check(em)
        except:
            return
        em.description = "```css\n" + em.description.lstrip("```css\n").rstrip("```").split("\n", 4)[4]

        # notify about using punch
        em.description += f"{attacker.name} threw a {bomb} on {enemy.name}\n"

        # get the random actions
        events = ["self", "missed", "hit", "hit", "critical", "critical"]
        events2 = ["rolled", "burst", "burst", "critical", "critical"]
        if b in (3, 4):
            events.remove("missed")
            events2.remove("rolled")
        if b == 4:
            events.remove("self")
        action1 = random.choice(events)
        action2 = random.choice(events2)

        if action1 != "self":
            if action1 == "missed":
                em.description += f"The bomb missed and rolled away\n...\n...\n"
                n = await self.damage(enemy, 0, o=em)
                if not n:
                    return
                em.description = n
            else:
                if action1 == "hit":
                    em.description += f"The bomb successfully got to {enemy.name}\n"
                elif action1 == "critical":
                    em.description += f"{enemy.name} had a critical damage from the impact with the bomb!!\n"
                    n = await self.damage(enemy, 2.5, o=em)
                    if not n:
                        return
                    em.description = n

                if action2 == "rolled":
                    em.description += f"The bomb just rolled away\n...\n"
                else:
                    if action2 == "burst":
                        em.description += f"The bomb blew up on the spot\n"
                        n = await self.damage(enemy, base_hit_damage, o=em)
                        if not n:
                            return
                        em.description = n
                    elif action2 == "critical":
                        em.description += f"The bomb critically burst up on the spot and did heavy damage\n"
                        n = await self.damage(enemy, base_hit_damage + 2, o=em)
                        if not n:
                            return
                        em.description = n

                    if b == 2 and random.choice([True, False]):
                        self.fighters["frozen"][str(enemy.id)] = datetime.datetime.utcnow()
                        em.description = "```css\n" + em.description.lstrip("```css\n").rstrip("```").split("\n", 1)[
                            1] + f"{enemy.name} is now frozen and will gain 1.25 times more damage for 10 seconds\n"
        else:
            em.description += f"{attacker.name} missed and the bomb target himself!\n"

            if action2 == "rolled":
                em.description += f"The bomb just rolled away\n...\n"
            else:
                if action2 == "burst":
                    em.description += f"The bomb blew up on the spot\n"
                    n = await self.damage(attacker, base_hit_damage, o=em)
                    if not n:
                        return
                    em.description = n
                elif action2 == "critical":
                    em.description += f"The bomb critically burst up on the spot and did heavy damage\n"
                    n = await self.damage(attacker, base_hit_damage + 2, o=em)
                    if not n:
                        return
                    em.description = n

                if b == 2 and random.choice([True, False]):
                    self.fighters["frozen"][str(attacker.id)] = datetime.datetime.utcnow()
                    em.description = "```css\n" + em.description.lstrip("```css\n").rstrip("```").split("\n", 1)[
                        1] + f"{attacker.name} is now frozen and will gain 1.25 times more damage for 10 seconds\n"

        em.description += "```"
        await self.change_current(enemy, o=em)

    async def ice_bomb(self):
        return await self.bomb(b=2)

    async def sticky_bomb(self):
        return await self.bomb(b=3)

    async def auto_aim_bomb(self):
        return await self.bomb(b=4)

    async def over(self, reason: str = "Fight timed out."):
        # update the player powers after battle
        d1 = await get_user_data(self.bot, self.user.id)
        d2 = await get_user_data(self.bot, self.enemy.id)
        now = datetime.datetime.utcnow()
        p1: dict = {}
        for key in d1[3].keys():
            item = d1[3][key]
            if not datetime.datetime.strptime(item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                count = int(item["count"])
                if count > 0:
                    if str(key) in self.fighters["powers"][str(self.user.id)].keys():
                        count = self.fighters["powers"][str(self.user.id)][str(key)]
                    p1[key] = {
                        "count": count,
                        "expires": item["expires"]
                    }
        await mysql_set(self.bot, self.user.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(p1))}'")
        await mysql_set(self.bot, self.user.id, arg1="players", arg2="bombs",
                        arg3=f'{self.fighters["powers"][str(self.user.id)]["bombs"]}')
        p2: dict = {}
        for key in d2[3].keys():
            item = d2[3][key]
            if not datetime.datetime.strptime(item["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                count = int(item["count"])
                if count > 0:
                    if str(key) in self.fighters["powers"][str(self.enemy.id)].keys():
                        count = self.fighters["powers"][str(self.enemy.id)][str(key)]
                    p2[key] = {
                        "count": count,
                        "expires": item["expires"]
                    }
        await mysql_set(self.bot, self.enemy.id, arg1="players", arg2="powers", arg3=f"'{str(json.dumps(p2))}'")
        await mysql_set(self.bot, self.enemy.id, arg1="players", arg2="bombs",
                        arg3=f'{self.fighters["powers"][str(self.enemy.id)]["bombs"]}')

        # release the players for another battle
        Currency.fighting.remove(self.user.id)
        Currency.fighting.remove(self.enemy.id)
        Currency.fighting.remove(self.message.guild.id)
        self.running = False
        try:
            await self.message.clear_reactions()
            await self.messagable.send(f"Fight over, reason: {reason}")
        except:
            pass


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
        m: discord.Message = None
        e = None

        async def wait_for_message():
            nonlocal m, e
            # Wait for a message by anyone in any guild or on exception run after another 5 minutes
            try:
                # Check if it is a valid guild channel
                def pred1(msg: discord.Message):
                    is_valid_guild_text_channel = not (
                            isinstance(msg.channel, discord.DMChannel) or isinstance(msg.channel,
                                                                                     discord.GroupChannel)) and isinstance(
                        msg.channel, discord.TextChannel)
                    if not is_valid_guild_text_channel:
                        return False
                    guild: discord.Guild = msg.guild
                    channel: discord.TextChannel = msg.channel
                    perms: discord.Permissions = channel.permissions_for(
                        discord.utils.get(guild.members, id=self.bot.user.id))
                    p_allowed = perms.send_messages and perms.use_external_emojis and perms.read_messages
                    return p_allowed

                m = await self.bot.wait_for('message', check=pred1, timeout=60)

                # Check random events allowed here, because it needs to be awaited
                random_events_allowed = await self.bot.config.get_random_events(m.guild.id)
                if not random_events_allowed:
                    # Wait for another message if the message's guild does not allow random_events
                    await wait_for_message()
            except asyncio.TimeoutError:
                # Wait again if timed out
                await wait_for_message()
            except Exception as ex:
                # Print any exception and return, do not let any exception raise else the loop will terminate
                print(ex)
                e = ex

        # Wait for a message to start a random event
        await wait_for_message()

        if not e and m:
            # Continues of if there was not any error, and the bot successfully received a message
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
                return tr

            try:
                if wait_for == "message":
                    message: discord.Message = await self.bot.wait_for('message', check=pred, timeout=timeout)
                    user = message.author
                elif wait_for == "reaction_add":
                    reaction, user = await self.bot.wait_for('reaction_add', check=pred, timeout=timeout)
                else:
                    raise ValueError("Unknown value for `wait_for`: " + wait_for)
            except asyncio.TimeoutError:
                await m.channel.send("The event expired, you all are lazy.")
            except Exception as e:
                print(e)  # If there is any other error, print it to the console and return to let the loop run
            else:
                gloves = "boxing_gloves"
                power = [x for x in self.bot.purchasables.keys() if str(x) != gloves and str(x) != "bombs"]
                powers = {}
                data = await get_user_data(self.bot, user.id)
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
                    await mysql_set(self.bot, user.id, arg1="players", arg2="powers",
                                    arg3=f"'{str(json.dumps(powers))}'")
                elif to_grant == gloves:
                    for key in data[3].keys():
                        value = data[3][key]
                        if not datetime.datetime.strptime(value["expires"], '%Y-%m-%d %H:%M:%S') <= now:
                            powers[key] = value
                    expire = now + datetime.timedelta(days=2, hours=12)
                    powers[gloves] = {"count": 1, "expires": f"{str(expire.strftime('%Y-%m-%d %H:%M:%S'))}"}
                    await mysql_set(self.bot, user.id, arg1="players", arg2="powers",
                                    arg3=f"'{str(json.dumps(powers))}'")
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
        print("Random events start")

    @random_events.after_loop
    async def after_random_events(self):
        # Random events loop has been terminated due to cog unload or an exception
        print("Random events end")

    async def get_user_image(self, user: discord.Member) -> BytesIO:
        """Returns BytesIO of an image set up with a background and the user avatar on it."""
        data = await get_user_data(self.bot, user.id)

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

    @commands.command(name="profile", aliases=["player", "flex"])
    async def player_stats(self, ctx, user: discord.User = None):
        """To get your info in the Bot's game"""
        if user is None:
            user = ctx.author
        user_stats = await get_user_data(self.bot, user.id)

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

    @commands.command(aliases=["purchase", "shop"])
    async def store(self, ctx, power: str = None, amount: int = 1):
        """To view or purchase a powerup for yourself."""
        # The valid purchasable items
        items = [x for x in self.bot.purchasables.keys()]
        s_help = f"The powerup {power} does not exist.\nTo buy a powerup use command `{ctx.prefix}store <powerup> " \
                 f"<amount>`\nFollowing are the valid items, each expire after 2 and a half days except normal bombs:\n"
        for i in range(len(items)):
            item = self.bot.purchasables[items[i]]
            s_help += f"{int(i) + 1}) `{items[i]}` {item['description']}\n"

        if power is None or power not in items:
            return await ctx.send(s_help)

        # Can not use command while fighting
        if ctx.author.id in self.fighting:
            return await ctx.send("You can not use this command while in battle")

        # Get the current data of the user
        data = await get_user_data(self.bot, ctx.author.id)

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
        data = await get_user_data(self.bot, ctx.author.id)

        # Return with sending a warning if the user is dead
        dead = data[5]
        if dead is not None:
            dead_time = datetime.datetime.utcnow() - dead
            if dead_time < datetime.timedelta(minutes=1, seconds=30):
                return await ctx.send(f"{ctx.author.mention}, You cannot use this command when dead.")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="dead", arg3='NULL')

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
        await p_session.run()

        if number is not None:
            try:
                i = self.bg_images[number - 1]
                del i
                await p_session.show_page(number - 1)
            except IndexError:
                return await ctx.send(f"Any background image does not exists at the number {number}.")

    @card_background.command()
    async def set(self, ctx, number: int):
        """To set a custom background image for your card."""
        # Can not use command while fighting
        if ctx.author.id in self.fighting:
            return await ctx.send("You can not use this command while in battle")

        # Get the current data of the user
        data = await get_user_data(self.bot, ctx.author.id)

        # Return with sending a warning if the user is dead
        dead = data[5]
        if dead is not None:
            dead_time = datetime.datetime.utcnow() - dead
            if dead_time < datetime.timedelta(minutes=1, seconds=30):
                return await ctx.send(f"{ctx.author.mention}, You cannot use this command when dead.")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="dead", arg3='NULL')

        try:
            image = self.bg_images[number - 1]
            data = await get_user_data(self.bot, ctx.author.id)

            # If user has enough tickets then continue else return warning
            if int(data[1]) < 50:
                return await ctx.send("You do not have enough credit for changing card background, it cost 35")

            # Deduct the credits and set the background
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="custom_bg", arg3=f"'{image}'")
            await mysql_set(self.bot, ctx.author.id, arg1="players", arg2="tickets", arg3=f'{str(int(data[1]) - 50)}')

            return await ctx.send("Successfully updated the background.")
        except IndexError:
            return await ctx.send("Any background image does not exists at the number.")

    @commands.command()
    @commands.cooldown(1, 86400, commands.cooldowns.BucketType.user)
    async def daily(self, ctx):
        await increment_ticket(self.bot, ctx.author.id, 25)
        await ctx.send("Awarded you 25 tickets for using the bot today!")

    @commands.command(aliases=["challenge", "fight", "battle"])
    @commands.cooldown(1, 5, commands.cooldowns.BucketType.guild)
    async def pvp(self, ctx, user: discord.User):
        if user.id == ctx.author.id and not await self.bot.is_owner(
                ctx.author):  # User can't fight themselves, but let the owners test
            return await ctx.send("You can not fight with yourself fool!")
        if user.bot:
            return await ctx.send("You can not fight with a bot fool!")

        # Can not use command while the user is fighting or someone else in the server is fighting
        if ctx.author.id in self.fighting:
            return await ctx.send("You are already in a battle.")
        if ctx.guild.id in self.fighting:
            return await ctx.send("Someone in this server is already in a battle.")

        # Example of a process that needs upvote

        if not await get_user_vote(self.bot, ctx.author.id):
            return await ctx.send(f"You need to upvote on my DBL page to use this command.")

        m: discord.Message = await ctx.send(
            f"{ctx.author.mention} has  challenged you {user.mention}, react with ✅ to accept the fight or ❌ to"
            f" reject the fight.")
        await m.add_reaction("✅")
        await m.add_reaction("❌")

        def react_check(r: discord.Reaction, u: discord.User):
            """Check to make sure it only responds to reactions from the current user and on the same message."""
            return r.message.id == m.id and r.emoji in ("✅", "❌") and u.id == user.id

        try:
            # waits for reaction using react_check
            reaction, user = await self.bot.wait_for('reaction_add', check=react_check, timeout=60)
        except asyncio.TimeoutError:
            return await ctx.send(f"{user.mention} you did not react in time, match canceled.")
        else:
            try:
                await m.delete()
            except:
                pass
            if reaction.emoji == "✅":
                fight = UsersFight(ctx, ctx.author, user)
                return await fight.run()
            else:
                return await ctx.send(f"Battle canceled by {user.name}.")


def setup(bot):
    bot.add_cog(Currency(bot))
