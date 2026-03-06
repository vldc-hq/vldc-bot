# Go Bot Staging Validation Runbook

## Scope

This runbook validates Go runtime parity before production cutover.

## Preconditions

- Staging bot token configured (`TOKEN`)
- Staging DB path configured (`SQLITE_DB_PATH`)
- Migrations applied (`make migrate-up`)
- Data copy dry-run validated (`make migrate-data`)
- Go bot started (`make go_run`)

## Checklist

1. Verify bot boot and graceful shutdown
   - Start bot, send SIGINT, ensure clean stop logs.
2. Verify command registration
   - Open Telegram command menu and check expected commands.
3. Verify core commands
   - `/start`, `/help`, `/version`.
4. Verify moderation commands (admin)
   - `/mute`, `/unmute`, `/ban`, `/trust`, `/untrust`.
5. Verify stateful commands
   - `/since`, `/since_list`, `/prism`, `/roll`, `/hussars`, `/gdpr_me`.
6. Verify mode toggles
   - `smile`, `towel`, `chat`, `fools`, `nastya` on/off/status.
7. Verify passive behavior
   - smile mode deletes text, towel mode quarantines newcomers, nastya mode blocks voice.
8. Verify scheduled jobs
   - AOC refresh job updates `aoc` row, chat mode periodic message appears.
9. Verify error reporting
   - Inject a forced handler error and confirm Sentry event is emitted.
10. Verify test and lint baseline
   - `go test ./...`, `go test -race ./...`, `make go_lint`.

## Exit Criteria

- All critical parity checks pass.
- No unresolved race/test failures.
- No critical Sentry errors during soak period.
