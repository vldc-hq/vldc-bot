package skill

import (
	"context"
	"math/rand/v2"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

const banmeMuteHours = 24

func BanmeSkill() appbot.Skill {
	return appbot.Skill{
		Name: "banme",
		Hint: "commit sudoku",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/banme", bot.MatchTypePrefix, handleBanme)
		},
	}
}

func handleBanme(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	msg := update.Message
	user := msg.From
	if user == nil {
		return
	}

	mult := rand.IntN(7) + 1 // 1-7 days
	duration := time.Duration(mult) * banmeMuteHours * time.Hour

	MuteUserForDuration(ctx, b, msg.Chat.ID, user.ID, user.FirstName, duration)
}
