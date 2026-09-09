# VLDC nyan bot ^_^

The official [VLDC](https://vldc.org) telegram group bot.

![nyan](img/VLDC_nyan-tiger-in-anaglyph-glasses.png)

[![Build Status](https://github.com/vldc-hq/vldc-bot/workflows/Nyan%20Bot/badge.svg)](https://github.com/vldc-hq/vldc-bot/actions?query=workflow%3A%22Nyan+Bot%22)
[![Maintainability](https://api.codeclimate.com/v1/badges/5941349dbc55ce7096fb/maintainability)](https://codeclimate.com/github/vldc-hq/vldc-bot/maintainability)


### Skills
* 😼 core –  core
* 😼 version –  show this message
* 😻 still – do u remember it?
* 😾 uwu –  don't uwu!
* 🤭 mute –  mute user for N minutes
* 🔫 roll –  life is so cruel... isn't it?
* ⚔️ banme –  commit sudoku
* 🔪 ban –  ban! ban! ban!
* 🎄 tree –  advent of code time!
* ⛔🤬 coc –  VLDC/GDG VL Code of Conduct
* 🛠 more than 70k? –  try to hire!
* 💻 got sk1lzz? –  put them to use!
* 👁 smell like PRISM? nononono!
* 💰 kozula Don't argue with kozula rate!
* 🤫 buktopuha Let's play a game 🤡

### Modes
* 😼 smile mode –  allow only stickers in the chat
* 🛠 since mode –  under construction
* 🧼 towel mode –  anti bot
* 🙃 fools mode –  what? not again!
* 🤫 nastya mode –  stop. just stop
* 🙃 chat mode - chatty Nyan

## Usage via VS Code (Easy Way)
Clone repository locally and open it up via VS Code and click Open in Container. Create `.env` file as described below.
Mongo will be available at `MONGO_HOST=localhost`. And you're done, you can run bot by clicking `F5` or `Run -> Launch Bot`.

Other option is to use [Codespaces](https://github.com/vldc-hq/vldc-bot/codespaces) from GitHub itself.

## Usage
Setup your env vars in `example.env` and rename it to `.env`. Don't push `.env` to public repos!

```
make up
```

## Daily cat encounter: `/kiskis`

Call the cat once per 24 hours. A call can give 24 hours of hussar time,
mute the caller for a day or five minutes (without hussar credit), offer a
choice of wet/dry food, or just produce a cat scene. Bonus time uses the
existing leaderboard; it does not increment shots, misses, or deaths.

There is also a one-minute chat cooldown. Hitting that cooldown does not
consume the caller's daily attempt. Personal cooldowns apply across chats.
The third consecutive call from the same user in a chat causes a five-minute
mute without hussar credit, including calls rejected by the personal cooldown.
Calls rejected by the shared chat pause also count toward this streak.
The second
call warns about this. Another caller or 24 hours without calls resets the
streak; restarting the bot does not. Further calls in that streak also hiss.
Cooldowns and pending food choices survive restarts in the configured SQLite
database. Gifts go to another previous `/kiskis` player in the same chat.
Food must be chosen by the caller within two minutes, once only.
Messages are cleaned up after two minutes (food results get two minutes
after resolution). The bot needs permission to restrict members and delete
messages; Telegram owners/admins are not demoted by this game.

Initial outcome weights: scratch 5, lick 10, gift 5, sleep 10, food 10,
harmless scenes 60. Gift is excluded when there are no other players.
Each food type is preferred with equal probability. Weights and phrases
live in `bot/skills/kiskis.py`.

For local Telegram testing use a separate bot/group and database. With Docker,
create `.local-test/` and set `SQLITE_DB_PATH=/app/.local-test/kiskis.db` in
the ignored `.env`, alongside `TOKEN` and `CHAT_ID`. Then run
`docker compose -f docker-compose-dev.yml up -d --build`.
Normal 24-hour/one-minute cooldowns apply in the live test too.

Automated coverage exercises every outcome, reward accounting, concurrent
claims, food callbacks, restart recovery and cleanup scheduling:
`PYTHONPATH=./bot SQLITE_DB_PATH=:memory: uv run pytest bot/tests/kiskis_test.py`.

## Local venv (no Docker)

Create a virtual environment and install dependencies locally:

```
make venv
source .venv/bin/activate
```

Run the bot locally:
```
PYTHONPATH=./bot python bot/main.py
```

Then run linters/tests with:
```
make lint
make test
```

## Build local image

```
make build
```

## Developing
Create test Telegram bot, and store TOKEN and chat id, you will need it for developing.

User `make` to up dev services:

```shell script
Usage: make [task]

task                 help
------               ----
build                Build all
up                   Up All and show logs
update               Restart bot after files changing
stop                 Stop all
down                 Down all
test                 Run tests
lint                 Run linters (black, flake8, mypy, pylint)
format               Format code (black)

help                 Show help message
```

Don't forget run `make lint` and `make test` before commit! For code formatting we are use [black](https://github.com/psf/black), so, just run `make format` to fire it :3

### Setting Up Debugger in VS Code

Create `launch.json` under your `.vscode` directory in project, add the following content onto it:
```
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Docker Python",
            "type": "python",
            "request": "attach",
            "port": 5678,
            "host": "localhost",
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ],
        }
    ]
}
```

Also, put `DEBUGGER=True` into your `.env` file. After that you can do debugging with VS Code, by running containerized application and hitting `Run -> Start Debugging` or `F5` button.

# Contributing
Bug reports, bug fixes and new features are always welcome.
Please open issues and submit pull requests for any new code.
