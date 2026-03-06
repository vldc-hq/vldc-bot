package skill

import (
	"context"
	"regexp"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

var uwuPattern = regexp.MustCompile(`(?i)\bu[wv]+u\b`)

func UwuSkill() appbot.Skill {
	return appbot.Skill{
		Name: "uwu",
		Hint: "anti-uwu filter",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil || update.Message.Text == "" {
					return false
				}
				return uwuPattern.MatchString(update.Message.Text)
			}, handleUwu)
		},
	}
}

func handleUwu(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:          update.Message.Chat.ID,
		Text:            "don't uwu! 😡",
		ReplyParameters: &models.ReplyParameters{MessageID: update.Message.ID},
	})
}
