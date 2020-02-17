# BombSquad Bot source code
This is the Github repository to share the source code of my BombSquad bot of discord,
 using this source code anyone can create and host their own bot with some tweaks and customization.
 The README files in this repository will provide you with all the information about the source code,
 and using the source code in different ways. For information about using the BombSquad bot and it's
 website go to [this repository's wiki pages](https://github.com/I-Am-The-Great/BombSquad-Bot/wiki).

## Py code evaluation
In the `bot.py` python script you see a thread named `RunInput` it is a non-blocking synchronous thread
 used to read commands from the command line after running the bot and the entered commands will be
 executed at the time of entry. so which means after running the bot from terminal, you can eval
 python code from the terminal in the bot scope.

Also there is a command added to the bot which name is `py_val`, it is also for similar purpose but
 used in discord servers, this command can be only used by discord users whose ids are added in `data/devs.json`.
 Using this command you can easily execute python code based on the current bot scope eg.
```
bs!py_val await bot.change_presence(activity=discord.Streaming(name=value, url='https://www.twitch.tv/a'), status='online')
```

## Using source code
You can use this source code in your own bot as long as th use complies with the terms of the License of this source code.
 To start, clone this repository and then do you changes in the files,
 like changing `creator_name`, `creator_url`, `creator_github` etc. in bot.py and the bot's developer's ID in `data/devs.json`
 Also if you wish to use moderation commands too, you have to change the file mod.py.bak to mod.py in `cogs` folder,
 then add the necessary permissions integer to the bot's invite line in `bot.py` in variable `bot_invite_perms`,
 for the sake of simplicity I have included the right permissions required in the same line in comment.

Make sure of following points before trying to run the bot:-
  1. You have python version >= 3.8.0
  2. You have all the requirements with correct version from the `requirements.txt`
  3. You must have `ffmpeg` installed for using audio cog
  4. You have correctly set up the environment variables required by this bot. Following are the environment variables required:
      - `bot_discord_token` this should be the token of the bot on discord's developer page
      - `bot_dbl_token` if your bot is listed in [DBL](https://top.gg) set this environment variable to bot's DBL token,
      or you may leave it
      - `mysql_user` the username used by the code to connect to MySQL database
      - `mysql_password` the password used by the code for establishment of the connection
      - `mysql_database` the database which has all data and which will be used by the code,
      for security and other reason it is recommended to use the same username and database name

And after you have done all changes and these points are ensured you can run the bot simply by opening a terminal in the root
 directory and type in the terminal `python bot.py` or `<python version/path> bot.py` based on your OS settings.

## Other README files
There are more README files spread in the directories on this branch of this repository.
The different README files are located at [cogs/README.md](/cogs/README.md), [data/README.md](/data/README.md), and [ext/README.md](/ext/README.md)

## Website
The source code used for the Website of BombSquad bot is also available on a seperate branch of this repository.
 The source code of the website is also documented with README files and is ready to be used with some of your tweaks.

## Contributing
If you wish to contribute to the source code of BombSquad Bot, you are allowed to do that by the means of issues or pull request.
 [More information about contributing here](/.github/CONTRIBUTING.md)

## Support
For getting support about this repository or the bot's source code, open an issue in this Github repository and we will help. 

## License
The source code of this bot is licensed under the `MIT` open source license.
