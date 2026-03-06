# VLDC nyan bot ^_^

The official [VLDC](https://vldc.org) telegram group bot. Written in Go.

![nyan](img/VLDC_nyan-tiger-in-anaglyph-glasses.png)

[![CI](https://github.com/vldc-hq/vldc-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/vldc-hq/vldc-bot/actions/workflows/ci.yml)

### Skills
* core - core bot functionality
* version - show bot version
* still - do u remember it?
* uwu - don't uwu!
* mute - mute user for N minutes
* roll - life is so cruel... isn't it?
* banme - commit sudoku
* ban - ban! ban! ban!
* tree - Advent of Code time!
* coc - VLDC/GDG VL Code of Conduct
* 70k - try to hire!
* pr - got sk1lzz? put them to use!
* prism - smell like PRISM? nononono!
* kozula - Don't argue with kozula rate!
* buktopuha - Let's play a game
* length - measure your instrument
* nya - Simon says wat?
* trusted - in god we trust
* aoc - Advent of Code tracker

### Modes
* smile mode - allow only stickers in the chat
* since mode - under construction
* towel mode - anti bot
* fools mode - what? not again!
* nastya mode - stop. just stop
* chat mode - chatty Nyan

## Quick Start

1. Copy `example.env` to `.env` and fill in your bot token and chat ID:
```
cp example.env .env
```

2. Run with Docker:
```
docker-compose -f docker-compose-dev.yml up
```

Or run locally:
```
make run
```

## Usage

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TOKEN` | Yes | Telegram bot token |
| `CHAT_ID` | Yes | Telegram group chat ID |
| `SQLITE_DB_PATH` | No | Path to SQLite database (default: `bot.db`) |
| `SENTRY_DSN` | No | Sentry DSN for error tracking |
| `AOC_SESSION` | No | Advent of Code session cookie |
| `GOOGLE_PROJECT_ID` | No | Google Cloud project ID (for translation) |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to Google service account JSON |
| `GEMINI_API_KEY` | No | Gemini API key (translation fallback) |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `DEBUG` | No | Enable debug logging |

### Make targets

```
make build          Build the bot binary
make run            Run the bot locally
make test           Run all tests
make test-cover     Run tests with coverage report
make lint           Run golangci-lint
make format         Format code with goimports
make tidy           Run go mod tidy
make docker-build   Build Docker image
make docker-up      Run with docker-compose
make docker-down    Stop docker-compose
```

## Developing

Create a test Telegram bot via [@BotFather](https://t.me/BotFather), store the token and your chat ID in `.env`.

Run linters and tests before committing:
```
make lint
make test
```

## Project Structure

```
cmd/bot/            - entry point
internal/
  bot/              - bot core, skill registration, middleware
  config/           - configuration loading
  db/               - SQLite database layer
  mode/             - mode state management
  skill/            - all bot skills (one file per skill)
  util/             - shared utilities (cleanup, etc.)
  ai/               - AI client helpers
```

# Contributing
Bug reports, bug fixes and new features are always welcome.
Please open issues and submit pull requests for any new code.
