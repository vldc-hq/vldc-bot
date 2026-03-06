package skill

import (
	"context"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

const smileModeName = "smile_mode"

func SmileModeSkill() appbot.Skill {
	return appbot.Skill{
		Name: "smile_mode",
		Hint: "sticker-only mode",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			deps.ModeState.Register(&mode.ModeConfig{
				Name:      smileModeName,
				DefaultOn: false,
			})

			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil {
					return false
				}
				return deps.ModeState.IsEnabled(update.Message.Chat.ID, smileModeName)
			}, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleSmileMode(ctx, b, update)
			})
		},
	}
}

func handleSmileMode(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	msg := update.Message

	// Allow stickers and animations (GIFs)
	if msg.Sticker != nil || msg.Animation != nil {
		return
	}

	// Delete everything else
	_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{
		ChatID:    msg.Chat.ID,
		MessageID: msg.ID,
	})
}
