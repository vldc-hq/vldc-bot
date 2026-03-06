# Go Production Cutover Checklist

## Pre-cutover

1. Confirm all `PLAN.md` tracks are marked `done`.
2. Ensure `go test ./...`, `go test -race ./...`, and `make go_lint` are green.
3. Run staging validation from `docs/staging-validation.md`.
4. Run one-time data copy dry-run:
   - `SOURCE_SQLITE_DB_PATH=<python-db> TARGET_SQLITE_DB_PATH=<go-db> make migrate-data`
5. Verify rollback steps from `docs/rollback.md` are executable.

## Cutover window

1. Stop Python bot process.
2. Snapshot Python SQLite DB.
3. Run final data copy to Go SQLite DB.
4. Start Go bot with production env.
5. Verify `/start`, `/help`, moderation and mode smoke checks.

## Post-cutover (first 24h)

1. Monitor Sentry error volume and critical command failure rate.
2. Validate scheduled jobs (AOC, chat mode, towel cleanup) are running.
3. Validate no data drift in key tables (`trusted_users`, `since_topics`, `roll_hussars`, `towel_quarantine`).

## Exit criteria

- No critical incidents for agreed observation period.
- Rollback no longer required for normal operation.
