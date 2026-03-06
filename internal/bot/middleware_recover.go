package bot

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/getsentry/sentry-go"
	tgbot "github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func recoveryMiddleware(logger *slog.Logger) tgbot.Middleware {
	return func(next tgbot.HandlerFunc) tgbot.HandlerFunc {
		return func(ctx context.Context, b *tgbot.Bot, update *models.Update) {
			defer func() {
				if r := recover(); r != nil {
					err := fmt.Errorf("panic recovered: %v", r)
					logger.Error("panic recovered in telegram handler", "error", err)
					sentry.CaptureException(err)
				}
			}()
			next(ctx, b, update)
		}
	}
}
