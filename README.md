# VLDC nyan bot ^_^

The official [VLDC](https://vldc.org) telegram group bot. 

![nyan](img/VLDC_nyan-tiger-in-anaglyph-glasses.png)


## Skills

### Smile Mode

Inspired by Twitch SmileMode this bot may bring you a remarkable new way to conversation ;)

If you an admin of Telegram Group just send `/on` to set SmileMode ON,
and `/off` to turn it off.

**Keep it in mind, you should make bot an admin and allow delete and pin messages**

On SmileMode all messages exclude **stickers** of **GIFs** will be deleted.

### Bot Gate

By default any new guests of the group will receive message from the Bot. 
User should reply the Bot message in the next hour otherwise user would be blacklisted.


## Usage
Replace `BOT_TOKEN` with your bot token, `YOUR_CHAT_ID` with your chat id and run command:

```
docker run --name vldc_bot -d --restart=always -e "TOKEN=BOT_TOKEN" -e "CHAT_ID=YOUR_CHAT_ID" egregors/vldc_bot
```

## Build local image

```
docker build -t vldcbot .
```

## Developing
Create VENV and install deps:
```
make dev
```

Start bot from VENV:
```
make start
```

# Contributing
Bug reports, bug fixes and new features are always welcome.
Please open issues and submit pull requests for any new code.
