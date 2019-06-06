# smile-bot

Inspired by Twitch SmileMode this bot may bring you a remarkable new way to conversation ;)

If you an admin of Telegram Group just send `/on` to set SmileMode ON,
and `/off` to turn it off.

**Keep it in mind, you should make bot an admin and allow delete and pin messages**

On SmileMode all messages exclude **stickers** of **GIFs** will be deleted.


## Usage
Replace `BOT_TOKEN` by your bot token and run command:

```
docker run --name smilebot -d --restart=always -e "TOKEN=BOT_TOKEN" egregors/smilebot
```

## Build local image

```
docker build -t smilebot .
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
