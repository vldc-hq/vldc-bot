package skill

import (
	"context"
	"fmt"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

func StillSkill() appbot.Skill {
	return appbot.Skill{
		Name: "still",
		Hint: "do u remember it?",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/still", bot.MatchTypePrefix, handleStill)
		},
	}
}

func handleStill(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	msg := update.Message

	text := extractArgs(msg.Text, "/still")
	if text == "" {
		return
	}

	year := convertYear(time.Now().Year())
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("Вот бы сейчас %s в %s лул 😹😹😹", text, year),
	})
	_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{ChatID: msg.Chat.ID, MessageID: msg.ID})
}

func convertYear(year int) string {
	century := year / 100
	remainder := year % 100
	if century%10 == 0 {
		return fmt.Sprintf("%dk%02d", century/10, remainder)
	}
	return fmt.Sprintf("%d", year)
}
