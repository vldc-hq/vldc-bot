package skill

import (
	"context"
	"fmt"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

const atLeast70kMessage = "Значительно больше откликов на предложение можно получить, " +
	"если подробно изложить суть, приложив по возможности ссылку на описание и " +
	"указав вилку :3"

func AtLeast70kSkill() appbot.Skill {
	return appbot.Skill{
		Name: "70k",
		Hint: "try to hire!",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/70k", bot.MatchTypePrefix, handle70k)
		},
	}
}

func handle70k(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	msg := update.Message

	text := atLeast70kMessage
	if msg.ReplyToMessage != nil && msg.ReplyToMessage.From != nil && msg.ReplyToMessage.From.Username != "" {
		text = fmt.Sprintf("@%s %s", msg.ReplyToMessage.From.Username, atLeast70kMessage)
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   text,
	})
}
