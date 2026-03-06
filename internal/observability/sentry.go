package observability

import (
	"context"
	"time"

	"github.com/getsentry/sentry-go"
)

type SentryShutdown func(ctx context.Context) error

func InitSentry(dsn string) (SentryShutdown, error) {
	if dsn == "" {
		return func(context.Context) error { return nil }, nil
	}

	err := sentry.Init(sentry.ClientOptions{Dsn: dsn})
	if err != nil {
		return nil, err
	}

	return func(ctx context.Context) error {
		timeout := 2 * time.Second
		if deadline, ok := ctx.Deadline(); ok {
			if until := time.Until(deadline); until > 0 {
				timeout = until
			}
		}

		sentry.Flush(timeout)
		return nil
	}, nil
}
