# Script extensions
This folder contains python scripts for the functions and classes that are not directly
 part of the bot's source code but is required to be used in the bot and is so imported
 at runtime when running the bot. 

## Config script
We know it sounds similar to the Config cog but it is different.

The `config.py` is the script containing `Config` class that is instantiated and used to
 set some necessary variables to bots and retrieve discord servers' configs at the
 runtime from the bot's MySQL database. For the sake of simplicity and no hardcoded
 database/row settings in all scripts, all of the code is just placed in this class and
 the functions are called from all over the bot commands.

## Update script
The `update.py` is a script also in the some folder containing the class `Update` and is
 little bit similar to the config script as the config script was for storing and
 retrieving config only, this is for updating the configs only.

## Utils script
The `utils.py` is a script that contains many utility functions which is used all over
 the scripts, it is the script used to define which should be only limited to the
 developer(s) of the bot, to paginate texts, and to execute the MySQL queries.

## Paginator script
It is the script the contains the `PaginatorSession` class which is used to paginate
 the embeds in the message using the reactions below te message and is very simple to
 use, as well as used in help command, with some special commands.