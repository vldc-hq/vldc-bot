package skill

import (
	"context"
	"log/slog"
	"strings"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

func NyaSkill() appbot.Skill {
	return appbot.Skill{
		Name: "nya",
		Hint: "Simon says wat?",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/nya", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				if update.Message == nil {
					return
				}
				msg := update.Message
				if !appbot.IsAdmin(ctx, b, msg.Chat.ID, msg.From.ID) {
					return
				}

				// Delete the command message
				_, err := b.DeleteMessage(ctx, &bot.DeleteMessageParams{
					ChatID:    msg.Chat.ID,
					MessageID: msg.ID,
				})
				if err != nil {
					slog.Info("can't delete msg", "error", err)
				}

				// Send args as text (Python behavior: `/nya some text` sends "some text")
				text := strings.TrimSpace(strings.TrimPrefix(msg.Text, "/nya"))
				if text == "" {
					return
				}
				_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
					ChatID: msg.Chat.ID,
					Text:   text,
				})
			})
		},
	}
}
