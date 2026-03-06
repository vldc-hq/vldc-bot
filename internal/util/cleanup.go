package util

import (
	"context"
	"log/slog"
	"time"

	"github.com/go-telegram/bot"
)

// ScheduleCleanup deletes the specified messages after delay.
// Runs in a background goroutine. Errors are logged and ignored.
func ScheduleCleanup(b *bot.Bot, chatID int64, delay time.Duration, messageIDs ...int) {
	if len(messageIDs) == 0 {
		return
	}
	go func() {
		time.Sleep(delay)
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		for _, id := range messageIDs {
			if id == 0 {
				continue
			}
			_, err := b.DeleteMessage(ctx, &bot.DeleteMessageParams{
				ChatID:    chatID,
				MessageID: id,
			})
			if err != nil {
				slog.Debug("cleanup: failed to delete message", "chat_id", chatID, "message_id", id, "error", err)
			}
		}
	}()
}
