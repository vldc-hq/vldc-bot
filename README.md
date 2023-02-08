# VLDC nyan bot ^_^

The official [VLDC](https://vldc.org) telegram group bot. 

![nyan](img/VLDC_nyan-tiger-in-anaglyph-glasses.png)

[![Build Status](https://github.com/vldc-hq/vldc-bot/workflows/Nyan%20Bot/badge.svg)](https://github.com/vldc-hq/vldc-bot/actions?query=workflow%3A%22Nyan+Bot%22)
![docker_hub](https://img.shields.io/docker/cloud/build/egregors/vldc_bot)
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

### Modes
* 😼 smile mode –  allow only stickers in the chat
* 🛠 since mode –  under construction
* 🧼 towel mode –  anti bot
* 🙃 fools mode –  what? not again!
* 🤫 nastya mode –  stop. just stop

## Usage via VS Code (Easy Way)
Clone repository locally and open it up via VS Code and click Open in Container. Create `.env` file as described below.
Mongo will be available at `MONGO_HOST=localhost`. And you're done, you can run bot by clicking `F5` or `Run -> Launch Bot`.

Other option is to use [Codespaces](https://github.com/vldc-hq/vldc-bot/codespaces) from GitHub itself.

## Usage
Setup your env vars in `example.env` and rename it to `.env`. Don't push `.env` to public repos!

```
make up
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
