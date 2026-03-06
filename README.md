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

## Usage (Go runtime)

The bot runs as a Go service under `cmd/nyanbot` and `internal/*`.

Required env vars:

- `TOKEN` - Telegram bot token

Optional env vars:

- `SQLITE_DB_PATH` (default: `bot.db`)
- `SENTRY_DSN`
- `DEBUG`
- `HTTP_TIMEOUT` (default: `30s`)
- `SHUTDOWN_TIMEOUT` (default: `10s`)
- `CHAT_ID` (for scheduled chat/aoc jobs)
- `AOC_SESSION` (for AOC private leaderboard refresh)
- `OPENAI_API_KEY` (chat mode AI fallback)
- `GEMINI_API_KEY` (chat mode AI fallback)

Run bot locally:

```sh
make go_run
```

Run checks:

```sh
make go_test
make go_cover
make go_lint
```

Run SQLite migrations:

```sh
make migrate-status
make migrate-up
```

One-time SQLite data copy for cutover dry-run:

```sh
SOURCE_SQLITE_DB_PATH=./bot.db TARGET_SQLITE_DB_PATH=./go-bot.db make migrate-data
```

Build container image:

```sh
docker build -f Dockerfile.nyan-go -t vldc-nyan-go:local .
```

Operational docs:

- `docs/staging-validation.md`
- `docs/cutover-checklist.md`
- `docs/rollback.md`

Development commands:

```sh
make go_run
make go_test
make go_cover
make go_lint
make migrate-status
make migrate-up
make migrate-data
make docker-build
```

# Contributing
Bug reports, bug fixes and new features are always welcome.
Please open issues and submit pull requests for any new code.
