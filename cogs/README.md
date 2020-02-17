# Bot's command extensions
This folder contains some python scripts that is loaded into bot's extensions at
 runtime. The extension classes containing bot commands or events that are loaded by
 bot are called Cogs.

These files are directly used by the bot and are the most necessary things as most of
 the commands resides in the Cogs in these scripts.

Different scripts have different cogs and they have different type of commands, similar
 to what their name states about the commands.

## Following are all the Cogs available to use :-

## Audio cog
This is the the cog which has the commands related to playing audio in the discord
 server's voice channels, like: join, play, leave.

## Config cog
This is the cog that contains the prefix customization command and the bs_stats command
 group with all of it's sub-commands.

## Fun cog
This cog is the home of all of the commands that is used for fun like: `bombjoke` and
 `trivia`.

## Info cog
This cog has 3 commands, `serverinfo`, `userinfo [user]` and `roleinfo <role>` for
 getting info of the discord server, yourself/any user, and a role respectively.

## Mod cog
This cog houses all moderation commands, which also requires some specific perms to be
 given to bot along with it the perms must also be there with the user to use it, ie. a
 moderator is required to use it.

Two reasons I have not included this cog in my bot:
  1. Special permissions required
  2. My bot is not made for moderation purpose it has special features

For the above reasons, I have disabled this cog, but you can enable it in your bot.
To enable this cog follow the given steps:-
  1. Rename it from `mod.py.bak` to `mod.py`
  2. Change the `bot_perms_integer` in `bot.py` with the required permissions integer
  (to help you, the necessary permission integer is given at the same line in comment)

## Utility cog
This cog has several commands and command groups that are very important and one of the
 special features of this bot. It also has some developer only commands to be used by
 the bot's developers only.
