# Go Rewrite Plan

Status: implementation baseline complete
Date: 2026-03-05
Branch: `feat/go-rewrite-plan`

## Goal

Rewrite the Telegram bot from Python to Go with a maintainable, production-ready stack:

- target Go `1.26.0` as the latest stable release at the time of planning
- keep the current bot behavior where it matters
- improve code structure, observability, CI, tests, and local developer workflow
- make future feature work cheaper than it is in the current codebase

Official Go release source: https://go.dev/doc/devel/release

## Current System Snapshot

Current Python implementation includes:

- polling-based Telegram bot bootstrap in `bot/main.py`
- command and mode registration through `bot/skills/*`
- custom command wrapper and admin checks in `bot/handlers.py`
- SQLite persistence in `bot/db/sqlite.py`
- env-based config in `bot/config.py`
- scheduled jobs through `python-telegram-bot` job queue
- external integrations:
  - Telegram Bot API
  - Sentry
  - Google Gemini
  - OpenAI
  - Google Translate
  - Google Speech-to-Text

Current domain areas already visible in the code:

- core commands and help
- moderation: mute, ban, trusted users
- game mechanics: roll, buktopuha
- chat and content modes: smile, since, towel, fools, nastya, chat
- speech recognition and generated content
- SQLite-backed state for trusted users, quarantine, topics, games, and counters

## Rewrite Principles

- Preserve behavior first, redesign internals second.
- Port in slices, not in one big bang.
- Keep the Python bot as the reference implementation until Go reaches feature parity.
- Prefer standard library where it is strong enough.
- Avoid CGO unless there is a hard technical reason to keep it.
- Make every subsystem testable without Telegram or cloud APIs.
- Treat testability as an architectural requirement, not as a property delegated to a Telegram library.

## Target Stack

### Language and project layout

- Go `1.26.0`
- single module repository
- `cmd/nyanbot` for the executable
- `internal/` packages for app, config, bot runtime, domain services, storage, and integrations
- `db/migrations` for schema changes

Suggested structure:

```text
cmd/nyanbot/
internal/app/
internal/config/
internal/bot/
internal/handlers/
internal/skills/
internal/modes/
internal/store/sqlite/
internal/ai/
internal/speech/
internal/translate/
internal/observability/
db/migrations/
test/
```

### Runtime and libraries

- Telegram: `github.com/go-telegram/bot`
- Logging: standard `log/slog`
- Config: environment-first, likely `github.com/caarlos0/env/v11` or a small in-house parser
- SQLite driver: `modernc.org/sqlite` to avoid CGO in CI and Docker
- Migrations: `github.com/pressly/goose/v3` or `github.com/golang-migrate/migrate/v4`
- Error reporting: Sentry Go SDK
- HTTP clients: standard `net/http` with explicit timeouts and dependency injection

### Quality gates

- formatter: `gofmt`, `gofumpt`
- linter: `golangci-lint`
- deeper static analysis: `staticcheck`
- security/vuln scan: `govulncheck`
- tests: `go test ./...`
- race detector in CI for supported packages: `go test -race ./...`
- coverage reporting for core packages

## Target Architecture

### Layers

- `internal/app`: process bootstrap, lifecycle, wiring
- `internal/config`: env parsing and validation
- `internal/bot`: Telegram adapter and update loop
- `internal/handlers`: reusable command/message handler composition
- `internal/skills`: command-level features
- `internal/modes`: long-lived chat modes and scheduled behavior
- `internal/store/sqlite`: repositories and transaction boundaries
- `internal/ai`, `internal/speech`, `internal/translate`: external service adapters behind interfaces
- `internal/observability`: logging, tracing hooks, Sentry integration, metrics if needed

### Key design choices

- domain logic should not depend directly on Telegram SDK types when avoidable
- business logic should sit behind our own interfaces and adapters so complex integration tests can run without real Telegram
- repositories should hide SQL details from feature code
- scheduled jobs should be explicit services, not scattered ad hoc timers
- AI providers should be wrapped behind interfaces so Gemini/OpenAI fallbacks stay testable
- configuration should fail fast on startup with clear validation errors

### Telegram testability approach

- do not write business logic directly against `*bot.Bot`
- define our own interfaces such as `TelegramGateway` for outgoing actions and `IncomingUpdate` for normalized inbound events
- keep Telegram SDK usage inside a thin adapter layer only
- feed synthetic incoming updates into the adapter with `ProcessUpdate` for integration-style tests
- verify outgoing Bot API calls through a fake `http.Client` or a local `httptest.Server`
- run adapter-level tests with `WithSkipGetMe()` and `WithNotAsyncHandlers()` to keep startup and handler execution deterministic

## Migration Strategy

### Phase 0. Discovery and freeze

- inventory all commands, modes, tables, env vars, background jobs, and cloud integrations
- document current behavior that must be preserved
- define what can intentionally change during the rewrite
- create a feature parity checklist from the existing Python bot

Deliverable:

- completed migration checklist linked to every current feature

### Phase 1. Go bootstrap

- initialize `go.mod`
- add `Makefile` targets for `fmt`, `lint`, `test`, `run`
- add base project layout under `cmd/` and `internal/`
- wire config loading, structured logging, graceful shutdown, Sentry bootstrap
- run a minimal Telegram bot with `/start` and `/help`

Deliverable:

- empty but bootable Go bot running against a test token

### Phase 2. Persistence and schema

- translate SQLite schema into migrations
- define repository interfaces and SQLite implementations
- add tests for repositories against temp databases
- confirm compatibility or write a one-time data migration script if schemas diverge

Deliverable:

- reproducible schema setup with tested repositories

### Phase 3. Core platform features

- implement command registration model
- implement admin checks and chat filtering
- implement scheduler abstraction for delayed and repeating jobs
- implement shared helpers for replies, moderation actions, and config-aware guards
- define our own Telegram gateway interfaces for incoming updates and outgoing actions instead of coupling feature code to a specific SDK
- implement the `go-telegram/bot` adapter so it can be driven by synthetic updates in tests and intercepted HTTP calls

Deliverable:

- Go runtime capable of supporting the existing feature model and offline integration tests

### Phase 4. Port low-risk features first

Recommended first batch:

- core help/start/version
- trusted users
- since mode and topic counters
- prism words
- simple moderation commands without AI dependencies

Deliverable:

- first useful parity slice with tests

### Phase 5. Port medium-complexity behavior

- roll
- mute
- ban
- length
- smile mode
- AOC-related behavior

Deliverable:

- moderation and stateful chat mechanics working in staging

### Phase 6. Port high-complexity and AI features

- towel mode
- chat mode
- buktopuha
- fools mode
- voice recognition
- Gemini/OpenAI fallback behavior

Deliverable:

- all cloud-backed and scheduled features working behind interfaces and tests/mocks

### Phase 7. Tooling, CI, and release pipeline

- add GitHub Actions for lint, tests, race, vuln scan, and build
- add multi-stage Dockerfile for Go service
- update local dev workflow and README
- optionally add pre-commit hooks

Deliverable:

- reproducible CI/CD workflow for the Go bot

### Phase 8. Cutover

- run the Go bot against a staging token/chat
- verify feature parity checklist
- migrate production config
- switch production deployment from Python to Go
- keep the Python code available briefly as rollback path until stability is proven

Deliverable:

- production cutover with rollback plan

## Testing Strategy

- unit tests for pure domain logic
- repository tests for SQLite behavior
- handler tests against our own gateway contracts instead of SDK internals
- integration tests for scheduler-driven flows
- end-to-end style integration tests that replay synthetic updates and assert outgoing bot actions without real Telegram
- adapter tests that drive `ProcessUpdate`, stub Bot API transport, and assert serialized outgoing Telegram requests
- golden tests where text formatting or generated prompts must stay stable
- explicit tests for permission checks and chat-scoped commands

Minimum CI contract:

- `gofmt` and `gofumpt` clean
- `golangci-lint` clean
- `go test ./...` clean
- `go test -race ./...` for supported packages
- `govulncheck ./...` clean

## Risks

- feature parity is larger than it first appears because the bot mixes commands, passive modes, timers, and AI calls
- Telegram library behavior may not map 1:1 to `python-telegram-bot`
- SQLite concurrency and timer-driven updates need careful testing
- AI-backed features are nondeterministic and need contract boundaries, not naive output assertions
- voice and translation integrations may need separate credential handling in Go
- production cutover cannot use the same token for Python and Go at the same time

## Non-Goals for the First Rewrite

- changing the product behavior just because Go makes it easy
- replacing SQLite with Postgres
- moving from polling to webhook in the same migration
- redesigning every command UX before parity is reached

## Definition of Done

The rewrite is done when:

- the Go bot covers all agreed production-critical features
- staging validation passes against the parity checklist
- CI enforces formatting, linting, tests, race checks, and vulnerability scan
- Docker and local dev workflow are documented and reproducible
- production runs the Go bot with monitoring and a rollback path

## Execution Backlog (Task Breakdown)

Task statuses: `todo`, `in-progress`, `blocked`, `done`

### Track A. Scope freeze and parity contract

- [x] A1 (`done`) Build feature inventory from Python code (`bot/main.py`, `bot/skills/*`, `bot/db/sqlite.py`, `bot/config.py`)
- [x] A2 (`done`) Build env var inventory and classify by domain (core, AI, speech, translation, moderation)
- [x] A3 (`done`) Build SQLite table/column inventory and map each table to feature owners
- [x] A4 (`done`) Build scheduled-job inventory (trigger, cadence, side effects, required state)
- [x] A5 (`done`) Define parity checklist with pass/fail criteria per feature
- [x] A6 (`done`) Mark explicit behavior changes allowed in v1 Go cutover (`PARITY_CHECKLIST.md`, section 11)

Acceptance for Track A:

- a single parity checklist exists and every current production-critical behavior maps to at least one testable checklist item

### Track B. Bootstrap and platform skeleton

- [x] B1 (`done`) Initialize `go.mod` and pin toolchain version
- [x] B2 (`done`) Create repository layout (`cmd/nyanbot`, `internal/*`, `db/migrations`, `test`)
- [x] B3 (`done`) Implement config loader with startup validation and typed config struct
- [x] B4 (`done`) Implement structured logging via `slog` with environment-aware level
- [x] B5 (`done`) Implement graceful shutdown and context-driven lifecycle in `internal/app`
- [x] B6 (`done`) Add Sentry bootstrap and panic/error capture wiring
- [x] B7 (`done`) Start minimal Telegram runtime with `/start` and `/help`

Acceptance for Track B:

- service boots locally with test token, handles `/start` and `/help`, and exits gracefully on signal

### Track C. Persistence and migrations

- [x] C1 (`done`) Choose migration tool (`goose`) and lock decision (`GOOSE_VERSION=v3.26.0`)
- [x] C2 (`done`) Port current SQLite schema to versioned migrations
- [x] C3 (`done`) Create migration Makefile targets (`migrate-up`, `migrate-down`, `migrate-status`)
- [x] C4 (`done`) Define repository interfaces for trusted users, quarantine, topics, games, counters
- [x] C5 (`done`) Implement SQLite repositories using explicit transaction boundaries
- [x] C6 (`done`) Add repository tests with temp DB fixtures
- [x] C7 (`done`) Add one-time SQLite data copy tool (`cmd/nyan-migrate`, `make migrate-data`) for cutover dry-runs

Acceptance for Track C:

- clean DB can be created from migrations and repository test suite passes

### Track D. Telegram adapter and handler model

- [x] D1 (`done`) Define transport-agnostic incoming/outgoing contracts (`IncomingUpdate`, `TelegramGateway`)
- [x] D2 (`done`) Implement `go-telegram/bot` adapter limited to translation layer
- [x] D3 (`done`) Implement command registration/composition model (initial registry + command specs)
- [x] D4 (`done`) Implement admin and permission guards as reusable middleware
- [x] D5 (`done`) Implement scheduler abstraction for delayed/repeating jobs
- [x] D6 (`done`) Add adapter-level tests with `ProcessUpdate`, `WithSkipGetMe`, `WithNotAsyncHandlers`
- [x] D7 (`done`) Add fake HTTP transport tests for outgoing Bot API payload assertions

Acceptance for Track D:

- feature code can be tested without real Telegram network calls

### Track E. Feature porting waves

- [x] E1 (`done`) Wave 1 (low-risk): help/start/version, trusted users, since mode, topic counters, prism words, basic moderation
- [x] E2 (`done`) Wave 2 (medium): roll, mute, ban, length, smile mode, AOC behavior (baseline parity implementation)
- [x] E3 (`done`) Wave 3 (high): towel mode, chat mode, buktopuha, fools mode, voice recognition, Gemini/OpenAI fallback (baseline parity implementation)
- [x] E4 (`done`) Add golden tests for output-sensitive features
- [x] E5 (`done`) Add permission and chat-scope tests for moderation features (baseline coverage)

Acceptance for Track E:

- every parity checklist item has either unit, repository, integration, or adapter test coverage

### Track F. CI/CD and operations

- [x] F1 (`done`) Add CI jobs: `gofmt`, `gofumpt`, `golangci-lint`, `go test ./...`, race, `govulncheck`
- [x] F2 (`done`) Add coverage report upload for core packages
- [x] F3 (`done`) Add multi-stage Dockerfile for Go runtime
- [x] F4 (`done`) Update README and local dev workflow
- [x] F5 (`done`) Define staging validation runbook and production cutover checklist
- [x] F6 (`done`) Define rollback procedure and cutoff criteria for Python fallback removal

Acceptance for Track F:

- CI is reproducible, staging validation is documented, and cutover has rollback steps

## Next Sprint Candidate (recommended)

1. A1-A5 (freeze parity contract)
2. B1-B7 (bootable Go skeleton)
3. C1-C3 (migration tooling baseline)
