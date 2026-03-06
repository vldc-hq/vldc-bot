# Python -> Go Parity Checklist

Status: draft (baseline extracted from current Python code)
Last update: 2026-03-06
Source of truth for extraction:

- `bot/main.py`
- `bot/skills/__init__.py`
- `bot/skills/*.py`
- `bot/db/sqlite.py`
- `bot/config.py`

## 1) Scope freeze decisions

- [ ] S1 Freeze production-critical features for v1 cutover
- [ ] S2 Freeze explicit non-parity changes allowed in v1 (if any)
- [ ] S3 Freeze Telegram adapter contract (`IncomingUpdate`/`TelegramGateway`) for Go

## 2) Environment variable inventory

Core/runtime:

- [ ] `TOKEN` (required): Telegram bot token
- [ ] `DEBUG` (optional): log level toggle
- [ ] `DEBUGGER` (optional): debugpy listener in Python
- [ ] `CHAT_ID` (optional): group chat id for scheduled announcements
- [ ] `SQLITE_DB_PATH` (optional, default `bot.db`)
- [ ] `SENTRY_DSN` (optional)

Feature-specific integrations:

- [ ] `AOC_SESSION` (AOC private leaderboard polling)
- [ ] `OPENAI_API_KEY` (AI fallback/features)
- [ ] `GEMINI_API_KEY` (AI fallback/features)
- [ ] `GOOGLE_PROJECT_ID` (fools mode image generation)
- [ ] `GOOGLE_APPLICATION_CREDENTIALS` (speech recognition)

Parity acceptance for env:

- [ ] E-ENV-1 Go startup fails fast for missing required vars (`TOKEN`)
- [ ] E-ENV-2 Optional vars preserve Python behavior when absent
- [ ] E-ENV-3 Integration-specific vars are validated at feature boundary with clear errors

## 3) SQLite schema inventory

Tables found in current Python DB init:

- [ ] `trusted_users` -> trusted mode / admin trust flow
- [ ] `buktopuha_players` -> BukToPuHa game state and scoreboard
- [ ] `towel_quarantine` -> towel mode quarantine and related messages
- [ ] `since_topics` -> since mode topic counters
- [ ] `roll_hussars` -> roll game stats and mute timing metrics
- [ ] `prism_words` -> prism word counters
- [ ] `peninsula_users` -> length/longest leaderboard data
- [ ] `aoc` -> cached Advent of Code payload

Parity acceptance for DB:

- [ ] E-DB-1 Migrations create schema equivalent to Python runtime schema
- [ ] E-DB-2 Repository behavior matches current semantics (insert/update/delete/order)
- [ ] E-DB-3 Datetime/json fields preserve read/write behavior and ordering assumptions

## 4) Scheduled jobs inventory

Known job-driven flows:

- [ ] J1 Mode cleanup jobs (`cleanup_queue_update` in `mode.py`) for auto-deleting bot/user messages
- [ ] J2 `aoc_mode` repeating update job (`JOB_AOC_UPDATE`) + immediate run on mode enable
- [ ] J3 `towel_mode` repeating job for quarantine checks/maintenance
- [ ] J4 `chat_mode` repeating job for periodic behavior
- [ ] J5 BukToPuHa one-shot hint/end jobs (`hint1-*`, `hint2-*`, `end-*`) with dedup by job name

Parity acceptance for jobs:

- [ ] E-JOB-1 No duplicate repeating jobs after mode toggles/restarts
- [ ] E-JOB-2 Job cancellation semantics match Python behavior
- [ ] E-JOB-3 Time-based actions are deterministic in tests via controllable scheduler abstraction

## 5) Feature parity checklist

Legend: critical = must pass before cutover; non-critical = can be postponed only with explicit sign-off.

### 5.1 Core bot lifecycle

- [ ] F-CORE-1 (critical) Bot starts with polling and handles updates
- [ ] F-CORE-2 (critical) `/start` responds
- [ ] F-CORE-3 (critical) `/help` responds
- [ ] F-CORE-4 (critical) `/version` responds and includes skills hints
- [ ] F-CORE-5 (critical) Bot command menu registration works (`setMyCommands` equivalent)
- [ ] F-CORE-6 (critical) Global error handler logs failures without crash loops

### 5.2 Admin/moderation and permissions

- [ ] F-MOD-1 (critical) Admin-gated commands enforce checks correctly
- [ ] F-MOD-2 (critical) `/mute` and `/unmute` behavior parity
- [ ] F-MOD-3 (critical) `/ban` behavior parity
- [ ] F-MOD-4 (non-critical) `/banme` behavior parity
- [ ] F-MOD-5 (critical) trusted mode commands (`/trust`, `/untrust`) parity

### 5.3 Commands and utility features

- [ ] F-CMD-1 (non-critical) `/still`
- [ ] F-CMD-2 (non-critical) `/uwu` passive filter behavior
- [ ] F-CMD-3 (non-critical) `/tree`
- [ ] F-CMD-4 (non-critical) `/pr`
- [ ] F-CMD-5 (non-critical) `/70k`
- [ ] F-CMD-6 (non-critical) `/coc`
- [ ] F-CMD-7 (non-critical) `/nya`
- [ ] F-CMD-8 (critical) `/roll`, `/hussars`, `/wipe_hussars`, `/gdpr_me`
- [ ] F-CMD-9 (non-critical) `/kozula`
- [ ] F-CMD-10 (non-critical) `/length`, `/longest`
- [ ] F-CMD-11 (critical) `/prism` + passive prism word tracking

### 5.4 Mode features

- [ ] F-MODE-1 (critical) `trusted_mode` on/off/status commands and default-state behavior
- [ ] F-MODE-2 (non-critical) `smile_mode` behavior parity
- [ ] F-MODE-3 (critical) `since_mode` behavior + topic counters parity
- [ ] F-MODE-4 (critical) `towel_mode` quarantine + AI moderation parity envelope
- [ ] F-MODE-5 (non-critical) `fools_mode` behavior parity
- [ ] F-MODE-6 (non-critical) `nastya_mode` behavior parity
- [ ] F-MODE-7 (critical) `chat_mode` behavior and scheduler parity
- [ ] F-MODE-8 (non-critical) `aoc_mode` periodic update parity

### 5.5 High-complexity integrations

- [ ] F-INT-1 (critical) Gemini/OpenAI fallback order and failure handling parity
- [ ] F-INT-2 (non-critical) Speech recognition flow parity
- [ ] F-INT-3 (non-critical) Translation/image-generation dependent flows parity
- [ ] F-INT-4 (critical) Sentry error reporting initialized and receiving runtime errors

## 6) Test mapping requirement (must be completed before cutover)

For each `F-*` and `E-*` item above:

- [ ] T1 Link at least one Go test case id/path
- [ ] T2 Mark test type (`unit`, `repo`, `integration`, `adapter`, `e2e-style`)
- [ ] T3 Record pass result in staging run

## 7) Open questions

- [ ] Q1 Confirm whether `aoc_mode`, `fools_mode`, and speech features are production-critical for first cutover
- [ ] Q2 Confirm acceptable behavior deltas for AI-generated text nondeterminism
- [ ] Q3 Confirm whether message-cleanup timing must be exact or within tolerance window

## 8) F-item source mapping and planned Go tests

### 8.1 Core bot lifecycle

- [ ] F-CORE-1 | source: `bot/main.py:69`, `bot/main.py:77` | priority: critical (runtime entrypoint gate) | tests: `integration` -> `test/parity/core_polling_boot_test.go`
- [ ] F-CORE-2 | source: `bot/skills/core.py:14`, `bot/skills/core.py:18` | priority: critical (basic liveness command) | tests: `adapter` -> `test/parity/core_start_command_test.go`
- [ ] F-CORE-3 | source: `bot/skills/core.py:15`, `bot/skills/core.py:26` | priority: critical (operator/user discoverability) | tests: `adapter` -> `test/parity/core_help_command_test.go`
- [ ] F-CORE-4 | source: `bot/skills/__init__.py:46`, `bot/skills/__init__.py:56` | priority: critical (ops visibility of deployed version) | tests: `adapter` -> `test/parity/core_version_command_test.go`
- [ ] F-CORE-5 | source: `bot/main.py:30`, `bot/skills/__init__.py:115` | priority: critical (Telegram UX contract) | tests: `integration` -> `test/parity/core_commands_registration_test.go`
- [ ] F-CORE-6 | source: `bot/main.py:38`, `bot/main.py:71` | priority: critical (fault containment) | tests: `integration` -> `test/parity/core_error_handler_test.go`

### 8.2 Admin/moderation and permissions

- [ ] F-MOD-1 | source: `bot/handlers.py:14`, `bot/permissions.py`, `bot/skills/nya.py:18` | priority: critical (security boundary) | tests: `adapter` -> `test/parity/mod_admin_guard_test.go`
- [ ] F-MOD-2 | source: `bot/skills/mute.py:22`, `bot/skills/mute.py:31`, `bot/skills/mute.py:155` | priority: critical (moderation core workflow) | tests: `adapter` -> `test/parity/mod_mute_unmute_test.go`
- [ ] F-MOD-3 | source: `bot/skills/ban.py:15`, `bot/skills/ban.py:18` | priority: critical (moderation core workflow) | tests: `adapter` -> `test/parity/mod_ban_test.go`
- [ ] F-MOD-4 | source: `bot/skills/banme.py:26`, `bot/skills/banme.py:29` | priority: non-critical (self-action utility) | tests: `adapter` -> `test/parity/mod_banme_test.go`
- [ ] F-MOD-5 | source: `bot/skills/trusted_mode.py:23`, `bot/skills/trusted_mode.py:31`, `bot/db/sqlite.py:117` | priority: critical (permission model dependency) | tests: `adapter+repo` -> `test/parity/mod_trust_commands_test.go`

### 8.3 Commands and utility features

- [ ] F-CMD-1 | source: `bot/skills/still.py:16` | priority: non-critical (utility command) | tests: `adapter` -> `test/parity/cmd_still_test.go`
- [ ] F-CMD-2 | source: `bot/skills/uwu.py:19`, `bot/skills/uwu.py:22` | priority: non-critical (passive reaction only) | tests: `adapter` -> `test/parity/cmd_uwu_filter_test.go`
- [ ] F-CMD-3 | source: `bot/skills/tree.py:27` | priority: non-critical (utility command) | tests: `adapter` -> `test/parity/cmd_tree_test.go`
- [ ] F-CMD-4 | source: `bot/skills/pr.py:20` | priority: non-critical (utility command) | tests: `adapter` -> `test/parity/cmd_pr_test.go`
- [ ] F-CMD-5 | source: `bot/skills/at_least_70k.py:20`, `bot/skills/at_least_70k.py:23` | priority: non-critical (utility command) | tests: `adapter` -> `test/parity/cmd_70k_test.go`
- [ ] F-CMD-6 | source: `bot/skills/coc.py:17` | priority: non-critical (utility command) | tests: `adapter` -> `test/parity/cmd_coc_test.go`
- [ ] F-CMD-7 | source: `bot/skills/nya.py:15`, `bot/skills/nya.py:24` | priority: non-critical (admin utility) | tests: `adapter` -> `test/parity/cmd_nya_test.go`
- [ ] F-CMD-8 | source: `bot/skills/roll.py:60`, `bot/skills/roll.py:67`, `bot/skills/roll.py:83`, `bot/skills/roll.py:398` | priority: critical (stateful game + moderation impact) | tests: `adapter+repo+integration` -> `test/parity/cmd_roll_suite_test.go`
- [ ] F-CMD-9 | source: `bot/skills/kozula.py:22` | priority: non-critical (utility command) | tests: `adapter` -> `test/parity/cmd_kozula_test.go`
- [ ] F-CMD-10 | source: `bot/skills/length.py:23`, `bot/skills/length.py:31`, `bot/db/sqlite.py:335` | priority: non-critical (leaderboard utility) | tests: `adapter+repo` -> `test/parity/cmd_length_longest_test.go`
- [ ] F-CMD-11 | source: `bot/skills/prism.py:29`, `bot/skills/prism.py:38`, `bot/db/sqlite.py:317` | priority: critical (passive state capture + reporting) | tests: `adapter+repo` -> `test/parity/cmd_prism_test.go`

### 8.4 Mode features

- [ ] F-MODE-1 | source: `bot/skills/trusted_mode.py:13`, `bot/mode.py:71` | priority: critical (baseline trust controls) | tests: `adapter+integration` -> `test/parity/mode_trusted_test.go`
- [ ] F-MODE-2 | source: `bot/skills/smile_mode.py:11`, `bot/skills/smile_mode.py:19` | priority: non-critical (chat policy mode) | tests: `adapter` -> `test/parity/mode_smile_test.go`
- [ ] F-MODE-3 | source: `bot/skills/since_mode.py:19`, `bot/skills/since_mode.py:27`, `bot/db/sqlite.py:238` | priority: critical (persistent topic counters) | tests: `adapter+repo` -> `test/parity/mode_since_test.go`
- [ ] F-MODE-4 | source: `bot/skills/towel_mode.py:53`, `bot/skills/towel_mode.py:157`, `bot/skills/towel_mode.py:219` | priority: critical (anti-spam + onboarding gate) | tests: `adapter+integration` -> `test/parity/mode_towel_test.go`
- [ ] F-MODE-5 | source: `bot/skills/fools.py:20`, `bot/skills/fools.py:31` | priority: non-critical (optional transform mode) | tests: `adapter` -> `test/parity/mode_fools_test.go`
- [ ] F-MODE-6 | source: `bot/skills/nastya_mode.py:15`, `bot/skills/nastya_mode.py:27` | priority: non-critical (voice moderation policy) | tests: `adapter` -> `test/parity/mode_nastya_test.go`
- [ ] F-MODE-7 | source: `bot/skills/chat.py:38`, `bot/skills/chat.py:195`, `bot/skills/chat.py:227` | priority: critical (scheduled AI behavior in group chat) | tests: `integration` -> `test/parity/mode_chat_test.go`
- [ ] F-MODE-8 | source: `bot/skills/aoc_mode.py:36`, `bot/skills/aoc_mode.py:48`, `bot/skills/aoc_mode.py:181` | priority: non-critical (time-bound seasonal feature) | tests: `integration` -> `test/parity/mode_aoc_test.go`

### 8.5 High-complexity integrations

- [ ] F-INT-1 | source: `bot/skills/towel_mode.py:243`, `bot/skills/towel_mode.py:255`, `bot/skills/buktopuha.py:270` | priority: critical (moderation correctness on provider failures) | tests: `integration` -> `test/parity/int_ai_fallback_test.go`
- [ ] F-INT-2 | source: `bot/skills/nastya_mode.py:11`, `bot/utils/recognition.py:48` | priority: non-critical (feature-specific external dependency) | tests: `integration` -> `test/parity/int_speech_test.go`
- [ ] F-INT-3 | source: `bot/skills/fools.py:80`, `bot/skills/fools.py:88`, `bot/skills/buktopuha.py:298` | priority: non-critical (optional external services) | tests: `integration` -> `test/parity/int_translate_gen_test.go`
- [ ] F-INT-4 | source: `bot/main.py:47` | priority: critical (production observability requirement) | tests: `integration` -> `test/parity/int_sentry_bootstrap_test.go`

## 9) Track parallelization constraints

- `Track A` is the contract gate; do `A1-A2` before parallel work.
- `Track B` and `Track C` can run in parallel after `A1-A2`.
- `Track D` starts after minimal outputs from `B` (app/runtime contracts) and `C` (repo interfaces).
- `Track E` starts after `D1-D3` and required repositories from `C`.
- `Track F1` can start early (right after `B1-B2`); `F3-F6` should follow when `D/E` stabilize.

## 10) Current Go implementation progress

Implemented in current Go baseline:

- [x] `/start`, `/help`, `/version`
- [x] Trusted user flows (`/trust`, `/untrust`)
- [x] Since flows (`/since`, `/since_list`)
- [x] Prism top command + passive prism word counting
- [x] Moderation baseline (`/ban`, `/mute`, `/unmute`)
- [x] Roll/hussars baseline (`/roll`, `/hussars`, `/wipe_hussars`, `/gdpr_me`)
- [x] Length flows (`/length`, `/longest`)
- [x] Mode toggles/status (`smile`, `towel`, `chat`, `fools`, `nastya`)
- [x] Buktopuha baseline (`/buktopuha`, passive guess flow, `/znatoki`)
- [x] AOC baseline (`/aoc_status`, `/aoc_refresh`, scheduled refresh)
- [x] AI fallback + speech/translation capability scaffolding

Validation status:

- [x] `go test ./...`
- [x] `go test -race ./...`
- [x] Adapter tests (`ProcessUpdate`, fake HTTP payload assertions)
- [x] Golden output test (help message)
- [x] Permission gating tests for admin-only commands
- [x] SQLite copy dry-run tool exists (`cmd/nyan-migrate`, `make migrate-data`)

## 11) Explicit v1 behavior deltas (approved for baseline)

- [x] DLT-1 Help output language/style is currently normalized and not byte-identical to Python bot.
- [x] DLT-2 Chat mode generation uses deterministic stub providers when API keys are present; full model prompts are postponed.
- [x] DLT-3 Towel mode intro moderation uses heuristic spam filter instead of full LLM moderation policy.
- [x] DLT-4 Buktopuha round timings/hints are simplified (10s/20s/30s) for baseline parity tests.
- [x] DLT-5 Fools/nastya translation/speech integrations are wired with disabled defaults unless credentials are configured.
