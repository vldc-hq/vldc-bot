package bot

import (
	"context"
	"log/slog"
	"strconv"
	"strings"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	"github.com/vldc-hq/vldc-bot/internal/config"
)

// chatFilterMiddleware rejects updates not from the configured group chat.
func chatFilterMiddleware(cfg *config.Config) bot.Middleware {
	return func(next bot.HandlerFunc) bot.HandlerFunc {
		return func(ctx context.Context, b *bot.Bot, update *models.Update) {
			chatID := extractChatID(update)
			if chatID == 0 {
				// No chat context (e.g., inline query) — pass through
				next(ctx, b, update)
				return
			}
			if !matchesChat(cfg.GroupChatID, chatID, extractChatUsername(update)) {
				slog.Debug("ignoring update from non-target chat", "chat_id", chatID)
				return
			}
			next(ctx, b, update)
		}
	}
}

func extractChatID(update *models.Update) int64 {
	if update.Message != nil {
		return update.Message.Chat.ID
	}
	if update.CallbackQuery != nil && update.CallbackQuery.Message.Message != nil {
		return update.CallbackQuery.Message.Message.Chat.ID
	}
	return 0
}

func extractChatUsername(update *models.Update) string {
	if update.Message != nil {
		return update.Message.Chat.Username
	}
	return ""
}

func matchesChat(configChatID string, chatID int64, chatUsername string) bool {
	if configChatID == "" {
		return true
	}
	// Try numeric match
	if id, err := strconv.ParseInt(configChatID, 10, 64); err == nil {
		return chatID == id
	}
	// Username match
	return strings.EqualFold(strings.TrimPrefix(configChatID, "@"), chatUsername)
}

// IsAdmin checks if the user is an admin in the chat.
func IsAdmin(ctx context.Context, b *bot.Bot, chatID, userID int64) bool {
	member, err := b.GetChatMember(ctx, &bot.GetChatMemberParams{
		ChatID: chatID,
		UserID: userID,
	})
	if err != nil {
		slog.Warn("admin check failed", "error", err)
		return false
	}
	return member.Type == "administrator" || member.Type == "creator"
}
