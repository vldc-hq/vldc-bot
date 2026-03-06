# Go Cutover Rollback Plan

## Rollback Triggers

- Command failure rate or handler errors exceed agreed threshold.
- Moderation commands do not enforce expected permissions.
- Data corruption detected in SQLite state tables.
- Critical integration failures (Telegram API, Sentry, AOC polling).

## Immediate Actions

1. Stop Go bot process.
2. Start Python bot with previous production environment.
3. Confirm health via `/start` and moderation smoke checks.
4. Announce rollback in ops channel with timestamp and reason.

## Data Safety

- Do not run destructive migrations during rollback window.
- Keep Go SQLite DB snapshot for postmortem.
- Keep Python DB untouched unless explicit migration required.

## Investigation Steps

1. Collect logs and Sentry errors from rollback interval.
2. Reproduce issue in staging with same config.
3. Add regression test before reattempting cutover.

## Re-cutover Gate

- Root cause fixed.
- Regression tests added and passing.
- Staging runbook fully green.
- Ops sign-off recorded.
