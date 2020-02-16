import discord
from discord.ext import commands
import os
import traceback
import asyncio


class Audio(commands.Cog):
    """A cog for adding the functionality to play BombSquad musics and remixes."""

    def __init__(self, bot):
        self.bot = bot

    async def audioStop(self, ctx):
        """To leave voice channel after done"""
        i = 0
        while i < 5:
            await asyncio.sleep(30)
            vc: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
            if vc is not None:
                if not vc.is_playing():
                    try:
                        await vc.disconnect()
                        await ctx.send("Left the voice channel due to half minute of inactivity.")
                        break
                    except:
                        traceback.print_exc()
                        break
            else:
                break
            i += 1

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel = None):
        """To make the bot join a voice channel."""
        if not channel and not ctx.author.voice:
            return await ctx.send('You are neither connected to a voice channel nor specified a channel to join.')
        destination = channel or ctx.author.voice.channel
        try:
            await destination.connect()
        except discord.ClientException:
            try:
                voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
            except discord.NotFound:
                return
            await voice_client.disconnect()
            try:
                await destination.connect()
            except discord.Forbidden:
                await ctx.send("I do not have access to that voice channel.")
        except discord.Forbidden:
            await ctx.send("I do not have access to that voice channel.")

    @commands.group(invoke_without_command=True)
    async def play(self, ctx):
        """To play either a BombSquad audio or remix."""
        await ctx.send(f"Usage: "
                       f"either `{ctx.prefix}play remix <number>`"
                       f"or `{ctx.prefix}play sound <search terms>`")

    @play.command()
    async def remix(self, ctx, music: int):
        """To play a BombSquad remix."""
        try:
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        except discord.NotFound:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if voice_client is not None:
            vc = voice_client
        else:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")

        if music == 1:
            name = "`Spaz in action` remix"
            audio_source = discord.FFmpegPCMAudio(
                source=os.path.join(self.bot.basedir, 'bsremixes/sia.ogg'))
        elif music == 2:
            name = "`Fall of BombSquad` remix"
            audio_source = discord.FFmpegPCMAudio(
                source=os.path.join(self.bot.basedir, 'bsremixes/fob.wav'))
        else:
            await vc.stop()
            await vc.disconnect()
            return await ctx.send("You did not specify a correct remix number.")

        try:
            vc.play(audio_source)
            await ctx.send(f"Now Playing: {name}")
        except discord.ClientException:
            return await ctx.send("Already playing an audio, stop the current audio or wait for completion of the "
                                  "current audio before playing next one.")

        await self.audioStop(ctx)

    @play.command()
    async def sound(self, ctx, search: str):
        """To play a BombSquad in-built audio"""
        try:
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        except discord.NotFound:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")

        if voice_client is not None:
            vc = voice_client
        else:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")

        audio_source = None
        name = None
        for sound in self.bot.bssounds:
            if str(sound).lower().__contains__(search.lower()):
                audio_source = discord.FFmpegPCMAudio(
                    source=os.path.join(self.bot.basedir, f'bssounds/{str(sound)}'))
                name = "`" + str(sound)[:-4] + "` audio."
                break

        if audio_source is None:
            return await ctx.send(f"No BombSquad audio found for `{search}`.")

        try:
            vc.play(audio_source)
            await ctx.send(f"Now Playing: {name}")
        except discord.ClientException:
            return await ctx.send("Already playing an audio, stop the current audio or wait for completion of the "
                                  "current audio before playing next one.")

        await self.audioStop(ctx)

    @commands.command()
    async def pause(self, ctx):
        """To pause the current playing audio."""
        try:
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        except discord.NotFound:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if voice_client is not None:
            vc = voice_client
        else:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if vc.is_playing():
            vc.pause()
            em = discord.Embed(title="Paused", description=f"Paused the current music.")
            await ctx.send(embed=em)
        else:
            await ctx.send("No music playing!")

    @commands.command()
    async def resume(self, ctx):
        """To resume the current paused audio."""
        try:
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        except discord.NotFound:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if voice_client is not None:
            vc = voice_client
        else:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if vc.is_paused():
            vc.resume()
            em = discord.Embed(title="Resumed", description=f"Resumed the current music.")
            await ctx.send(embed=em)
        else:
            await ctx.send("No music paused!")

    @commands.command()
    async def stop(self, ctx):
        """To stop the current audio."""
        try:
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        except discord.NotFound:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if voice_client is not None:
            vc = voice_client
        else:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if vc.is_connected() and (vc.is_paused() or vc.is_playing()):
            vc.stop()
            em = discord.Embed(title="Stopped", description=f"Stopped the current music.")
            await ctx.send(embed=em)
            await asyncio.sleep(30)
            if not vc.is_playing():
                await vc.disconnect()
        else:
            await ctx.send("No music playing or no channel joined!")

    @commands.command(aliases=["leave"])
    async def disconnect(self, ctx):
        """To make the bot leave the voice channel."""
        try:
            voice_client: discord.VoiceClient = discord.utils.get(self.bot.voice_clients, guild=ctx.guild)
        except discord.NotFound:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        if voice_client is not None:
            vc = voice_client
        else:
            return await ctx.send(
                f"I am not in any channel, first use the join command in a voice channel: `{ctx.prefix}join`")
        await vc.disconnect(force=True)


def setup(bot):
    bot.add_cog(Audio(bot))
