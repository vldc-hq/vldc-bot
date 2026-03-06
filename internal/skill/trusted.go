package skill

import (
	"context"
	"fmt"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/db"
)

func TrustedSkill() appbot.Skill {
	var database *db.DB

	return appbot.Skill{
		Name: "trusted",
		Hint: "trust/untrust users",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB

			b.RegisterHandler(bot.HandlerTypeMessageText, "/trust", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleTrust(ctx, b, update, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/untrust", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleUntrust(ctx, b, update, database)
			})
		},
	}
}

func handleTrust(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil || update.Message.ReplyToMessage == nil {
		return
	}
	msg := update.Message
	if !appbot.IsAdmin(ctx, b, msg.Chat.ID, msg.From.ID) {
		return
	}

	target := msg.ReplyToMessage.From
	if target == nil {
		return
	}

	already, _ := database.IsUserTrusted(target.ID)
	if already {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("%s is already trusted 😼👍", displayName(target)),
		})
		return
	}

	if err := database.TrustUser(target.ID, msg.From.ID); err != nil {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("Failed to trust: %s", err),
		})
		return
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("%s is trusted now! 😼🤝😐", displayName(target)),
	})
}

func handleUntrust(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil || update.Message.ReplyToMessage == nil {
		return
	}
	msg := update.Message
	if !appbot.IsAdmin(ctx, b, msg.Chat.ID, msg.From.ID) {
		return
	}

	target := msg.ReplyToMessage.From
	if target == nil {
		return
	}

	if err := database.UntrustUser(target.ID); err != nil {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("Failed to untrust: %s", err),
		})
		return
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("%s lost confidence... 😼🖕", displayName(target)),
	})
}
