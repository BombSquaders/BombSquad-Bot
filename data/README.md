# Bot static data

This folder contains some json files, the json files contains the data the bot uses,
 but not change at the runtime.
 
Those data include the jokes, the trivia questions, and bot's developers' discord user
 account's IDs.

These data are each stored as a custom attribute of the bot at the time of
 instantiating the Config class and is stored in bot's cache, when the Config class
 or bot itself reloads the data is refreshed.
