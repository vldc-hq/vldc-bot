# VLDC nyan bot ^_^

The official [VLDC](https://vldc.org) telegram group bot. 

![nyan](img/VLDC_nyan-tiger-in-anaglyph-glasses.png)

[![Build Status](https://github.com/vldc-hq/vldc-bot/workflows/Nyan%20Bot/badge.svg)](https://github.com/vldc-hq/vldc-bot/actions?query=workflow%3A%22Nyan+Bot%22)
![docker_hub](https://img.shields.io/docker/cloud/build/egregors/vldc_bot)
[![Maintainability](https://api.codeclimate.com/v1/badges/baa6fa307ee9f8411c5d/maintainability)](https://codeclimate.com/github/vldc-hq/vldc-bot/maintainability)


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

### Modes
* 😼 smile mode –  allow only stickers in the chat
* 🛠 since mode –  under construction
* 🧼 towel mode –  anti bot
* 🙃 fools mode –  what? not again!
* 🦠 covid mode –  fun and gamez
* 🤫 nastya mode –  stop. just stop


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

User `make` to up dev services:

```shell script
Usage: make [task]

task                 help
------               ----
build                Build all
up                   Up All and show logs
stop                 Stop all
down                 Down all
test                 Run tests
lint                 Run linters (flake8, mypy)
                     
help                 Show help message
```

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
