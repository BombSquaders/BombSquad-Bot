import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
import random
import aiohttp
import asyncio
from ext import utils


class Misc(commands.Cog):
    """But fun commands."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['8ball'])
    @commands.cooldown(1, 8, BucketType.user)
    async def eightball(self, ctx, *, question: str):
        """Ask the 8 ball a question"""
        if not question.endswith('?'):
            return await ctx.send('Please ask a question.')

        responses = ["It is certain", "It is decidedly so", "Without a doubt", "Yes definitely",
                     "You may rely on it", "As I see it, yes", "Most likely", "Outlook good",
                     "Yes", "Signs point to yes", "Reply hazy try again", "Ask again later",
                     "Better not tell you now", "Cannot predict now", "Concentrate and ask again",
                     "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good",
                     "Very doubtful"]

        num = random.randint(0, len(responses) - 1)
        if num < 10:
            em = discord.Embed(color=discord.Color.green())
        elif num < 15:
            em = discord.Embed(color=discord.Color(value=0xffff00))
        else:
            em = discord.Embed(color=discord.Color.red())

        response = responses[num]

        em.title = f"🎱{question}"
        em.description = response
        await ctx.send(embed=em)

    @commands.command(aliases=['coin'])
    @commands.cooldown(1, 1.25, BucketType.user)
    async def flipcoin(self, ctx, noembed: str = None):
        """Flips a coin"""
        choices = ['You got Heads', 'You got Tails']
        if noembed is not None and str(noembed).endswith("noembed"):
            await ctx.send("Coinflip: " + random.choice(choices))
        else:
            color = utils.random_color()
            em = discord.Embed(color=color, title='Coinflip:', description=random.choice(choices))
            em.set_footer(text="Suffix the command with ` noembed` for getting the result without embed on mobile.")
            await ctx.send(embed=em)

    @commands.command()
    @commands.cooldown(1, 2.5, BucketType.user)
    async def dice(self, ctx, number=1, noembed: str = None):
        """Rolls a certain number of dice less or equal to 10"""
        if number > 10:
            number = 10

        fmt = ''
        for i in range(1, number + 1):
            fmt += f'`Dice {i}: {random.randint(1, 6)}`\n'

        if noembed is not None and str(noembed).endswith("noembed"):
            m = f"{str(number)} Dice rolled:\n" + fmt
            await ctx.send(m)
        else:
            color = utils.random_color()
            em = discord.Embed(color=color, title='Roll a certain number of dice', description=fmt)
            em.set_footer(text="Suffix the command with ` noembed` for getting the result without embed on mobile.")
            await ctx.send(embed=em)

    @commands.command(aliases=['lotto'])
    @commands.cooldown(1, 60, BucketType.user)
    async def lottery(self, ctx, n1: int, n2: int, n3: int):
        """Enter the lottery and see if your guesses makes you win!"""
        author = ctx.author
        numbers = []
        for x in range(3):
            numbers.append(random.randint(1, 5))

        if numbers[0] == n1 and numbers[1] == n2 and numbers[2] == n3:
            await ctx.send(f'{author.mention} You won! Congratulations on winning the lottery!')
        else:
            await ctx.send(
                f"{author.mention} Better luck next time... You were one of the 124/125 who lost the lottery...\n"
                f"The numbers were `{', '.join([str(x) for x in numbers])}`")

    @commands.command(aliases=['xkcd', 'comic'])
    async def randomcomic(self, ctx):
        """Get a comic from xkcd."""

        # Example of a command that needs upvote
        if self.bot.dbl_client is not None:
            voted = await self.bot.dbl_client.get_user_vote(ctx.author.id)
        else:
            voted = True
        if not voted:
            return await ctx.send(f"You need to upvote on my DBL page to use this command ({ctx.command.prefix}upvote)")

        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://xkcd.com/info.0.json') as resp:
                data = await resp.json()
                current_comic = data['num']
        rand = random.randint(0, current_comic)  # max = current comic
        async with aiohttp.ClientSession() as session:
            async with session.get(f'http://xkcd.com/{rand}/info.0.json') as resp:
                data = await resp.json()
        em = discord.Embed(color=utils.random_color())
        em.title = f"XKCD Number {data['num']}- \"{data['title']}\""
        em.set_footer(text=f"Published on {data['month']}/{data['day']}/{data['year']}")
        em.set_image(url=data['img'])
        await ctx.send(embed=em)

    @commands.command(aliases=['number'])
    async def numberfact(self, ctx, number: int):
        """Get a fact about a number."""
        if not number:
            await ctx.send(f'Usage: `{ctx.prefix}numberfact <number>`')
            return
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://numbersapi.com/{number}?json') as resp:
                    file = await resp.json()
                    fact = file['text']
                    await ctx.send(f"**Did you know?**\n*{fact}*")
        except KeyError:
            await ctx.send("No facts are available for that number.")

    @commands.command(aliases=["joke"])
    async def bombjoke(self, ctx):
        """Get a bomb joke."""
        joke = random.choice(self.bot.jokes["titles"])
        em = discord.Embed(color=utils.random_color())
        em.title = str(joke)
        em.description = "||" + str(self.bot.jokes["punchlines"][joke]) + "||"
        em.set_footer(text="Bomb Joke")
        await ctx.send(embed=em)

    @commands.command()
    @commands.cooldown(1, 5, BucketType.user)
    async def trivia(self, ctx):
        """Get a trivia of questions related to the BombSquad game."""
        trivia = self.bot.trivias[random.choice([x for x in self.bot.trivias])]
        options = trivia["options"]
        answers = trivia["answers"]
        em = discord.Embed(color=utils.random_color())
        em.title = str(trivia["question"])
        em.description = "Send in chat the correct option."
        number = 0
        for option in options:
            number += 1
            em.add_field(name=f"{number}", value=str(option))
        em.set_footer(text="Answer in 15 secs.")
        await ctx.send(embed=em)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.message.channel

        try:
            reply = await self.bot.wait_for('message', check=check, timeout=15.0)
        except asyncio.TimeoutError:
            return await ctx.send("You took much time.")
        if str(reply.content) in answers:
            await ctx.send("Congratulations! You won the trivia.")
        else:

            await ctx.send("Unfortunately, you lost the trivia.\n"
                           "Better luck next time.\n"
                           f"The answer was: {answers[1]}")


def setup(bot):
    bot.add_cog(Misc(bot))
