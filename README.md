# VLDC nyan bot ^_^

The official [VLDC](https://vldc.org) telegram group bot. 

![nyan](img/VLDC_nyan-tiger-in-anaglyph-glasses.png)

![docker_hub](https://img.shields.io/docker/cloud/build/egregors/vldc_bot)
[![Maintainability](https://api.codeclimate.com/v1/badges/baa6fa307ee9f8411c5d/maintainability)](https://codeclimate.com/github/egregors/vldc-bot/maintainability)

## Skills

### Smile Mode

Inspired by Twitch SmileMode this bot may bring you a remarkable new way to conversation ;)

If you an admin of Telegram Group just send `/smile_mode-on` to set SmileMode ON,
and `/smile_mode_off` to turn it off.

**Keep it in mind, you should make bot an admin and allow delete and pin messages**

On SmileMode all messages exclude **stickers** of **GIFs** will be deleted.

### Bot Gate

By default any new guests of the group will receive message from the Bot. 
User should reply the Bot message in the next hour otherwise user would be blacklisted.


## Usage
Setup your env vars in `example.env` and rename it to `.env`. Don't push `.env` to public repos!

```
docker-compose up -d && docker-compose logs -f --tail=10
```

## Build local image

```
docker-compose -f docker-compose-dev.yml build
```

## Developing
Create test Telegram bot, and store TOKEN and chat id, you will need it for developing.

### In VENV:

Create `venv` and install dependencies
```
make dev
```

Run tests
```
make test
```

Run linters
```
make lint
```

Run bot (required vars should be in ENV)
```
make start
```

### In Docker:

Build local container
```
make dev_build
```

Run local dev bot (with mongo)
```
dev_start
```

Run tests
```
make dev_test
```

# Contributing
Bug reports, bug fixes and new features are always welcome.
Please open issues and submit pull requests for any new code.