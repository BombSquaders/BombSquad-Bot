import discord
from discord.ext import commands
from ext.paginator import PaginatorSession
from ext import utils


class Info(commands.Cog):
    """Get info for a user, server, or role."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['si', 'server'])
    async def serverinfo(self, ctx):
        """Get server info"""

        # Get the discord guild's info and send

        guild = ctx.guild
        guild_age = (ctx.message.created_at - guild.created_at).days
        created_at = f"Server created on {guild.created_at.strftime('%b %d %Y at %H:%M')}. That\'s over " \
                     f"{guild_age} days ago!"
        color = utils.random_color()

        em = discord.Embed(description=created_at, color=color)
        em.add_field(name='Online Members',
                     value=str(len({m.id for m in guild.members if m.status is not discord.Status.offline})))
        em.add_field(name='Total Members', value=str(len(guild.members)))
        em.add_field(name='Text Channels', value=str(len(guild.text_channels)))
        em.add_field(name='Voice Channels', value=str(len(guild.voice_channels)))
        em.add_field(name='Roles', value=str(len(guild.roles)))
        em.add_field(name='Owner', value=guild.owner)

        if guild.icon_url:
            em.set_thumbnail(url=guild.icon_url)
        if guild.icon_url:
            em.set_author(name=guild.name, icon_url=guild.icon_url)
        else:
            em.set_author(name=guild.name)

        # Add the time the bot joined this guild
        em.set_footer(text="Joined this guild on " + await self.bot.config.get_guild_add_time(guild.id))
        await ctx.send(embed=em)

    @commands.command(aliases=['ui', 'user'])
    async def userinfo(self, ctx, user: discord.Member = None):
        """Get user info for yourself or someone in the guild"""

        # Get the user
        user = user or ctx.message.author
        guild = ctx.message.guild
        guild_owner = guild.owner
        avi = user.avatar_url

        # Get the user roles
        roles = sorted(user.roles, key=lambda r: r.position)
        for role in roles:
            if str(role.color) != '#000000':
                color = role.color
        if 'color' not in locals():
            color = 0
        role_names = ', '.join([r.name for r in roles if r != '@everyone']) or 'None'

        # Now add the general info
        time = ctx.message.created_at
        desc = f'{user.name} is currently in {user.status} mode.'
        member_number = sorted(guild.members, key=lambda m: m.joined_at).index(user) + 1
        em = discord.Embed(color=utils.random_color(), description=desc, timestamp=time)
        em.add_field(name='Name', value=user.name),
        em.add_field(name='Member Number', value=str(member_number)),
        em.add_field(name='Account Created', value=user.created_at.__format__('%A, %B %d, %Y')),
        em.add_field(name='Join Date', value=user.joined_at.__format__('%A, %B %d, %Y')),
        em.add_field(name='Roles', value=role_names)
        em.set_thumbnail(url=avi or None)
        await ctx.send(embed=em)

    @commands.command(aliases=['role'])
    async def roleinfo(self, ctx, *, role_name):
        """Get information about a role. Case Sensitive!"""

        # Get the role or return
        role = discord.utils.get(ctx.message.guild.roles, name=role_name)
        if not role:
            return await ctx.send(f"Role could not be found. The system IS case sensitive!")

        # Get the role permissions
        em = discord.Embed(description=f'Role ID: {str(role.id)}', color=role.color or utils.random_color())
        em.title = role.name
        perms = ""
        if role.permissions.administrator:
            perms += "Administrator, "
        if role.permissions.create_instant_invite:
            perms += "Create Instant Invite, "
        if role.permissions.kick_members:
            perms += "Kick Members, "
        if role.permissions.ban_members:
            perms += "Ban Members, "
        if role.permissions.manage_channels:
            perms += "Manage Channels, "
        if role.permissions.manage_guild:
            perms += "Manage Guild, "
        if role.permissions.add_reactions:
            perms += "Add Reactions, "
        if role.permissions.view_audit_log:
            perms += "View Audit Log, "
        if role.permissions.read_messages:
            perms += "Read Messages, "
        if role.permissions.send_messages:
            perms += "Send Messages, "
        if role.permissions.send_tts_messages:
            perms += "Send TTS Messages, "
        if role.permissions.manage_messages:
            perms += "Manage Messages, "
        if role.permissions.embed_links:
            perms += "Embed Links, "
        if role.permissions.attach_files:
            perms += "Attach Files, "
        if role.permissions.read_message_history:
            perms += "Read Message History, "
        if role.permissions.mention_everyone:
            perms += "Mention Everyone, "
        if role.permissions.external_emojis:
            perms += "Use External Emojis, "
        if role.permissions.connect:
            perms += "Connect to Voice, "
        if role.permissions.speak:
            perms += "Speak, "
        if role.permissions.mute_members:
            perms += "Mute Members, "
        if role.permissions.deafen_members:
            perms += "Deafen Members, "
        if role.permissions.move_members:
            perms += "Move Members, "
        if role.permissions.use_voice_activation:
            perms += "Use Voice Activation, "
        if role.permissions.change_nickname:
            perms += "Change Nickname, "
        if role.permissions.manage_nicknames:
            perms += "Manage Nicknames, "
        if role.permissions.manage_roles:
            perms += "Manage Roles, "
        if role.permissions.manage_webhooks:
            perms += "Manage Webhooks, "
        if role.permissions.manage_emojis:
            perms += "Manage Emojis, "

        if perms is None:
            perms = "None"
        else:
            perms = perms.strip(", ")

        # General role settings
        em.add_field(name='Hoisted', value=str(role.hoist))
        em.add_field(name='Position from bottom', value=str(role.position))
        em.add_field(name='Managed by Integration', value=str(role.managed))
        em.add_field(name='Mentionable', value=str(role.mentionable))
        em.add_field(name='People in this role', value=str(len(role.members)))

        em2 = discord.Embed(description=f'Role ID: {str(role.id)}', color=role.color or discord.Color.green())
        em2.title = role.name
        em2.add_field(name='Permissions', value=perms)

        pages = [em, em2]

        thing = str(role.created_at.__format__('%A, %B %d, %Y'))

        # Start the pagination session
        p_session = PaginatorSession(ctx, footer=f'Created At: {thing}', pages=pages)
        await p_session.run()


def setup(bot):
    bot.add_cog(Info(bot))
