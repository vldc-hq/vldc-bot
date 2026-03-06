package skill

import (
	"context"
	"fmt"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

const prMessage = "Would you like to make PR for this?\n" +
	"You can start by forking me at https://github.com/vldc-hq/vldc-bot\n" +
	"💪😎"

func PrSkill() appbot.Skill {
	return appbot.Skill{
		Name: "pr",
		Hint: "got sk1lzz?",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/pr", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				if update.Message == nil {
					return
				}
				msg := update.Message

				text := prMessage
				if msg.ReplyToMessage != nil && msg.ReplyToMessage.From != nil && msg.ReplyToMessage.From.Username != "" {
					text = fmt.Sprintf("@%s %s", msg.ReplyToMessage.From.Username, prMessage)
				}

				_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
					ChatID: msg.Chat.ID,
					Text:   text,
				})
			})
		},
	}
}
