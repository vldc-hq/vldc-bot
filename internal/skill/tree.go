package skill

import (
	"context"
	"fmt"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

const aocLeaderboardID = "458538"

func TreeSkill() appbot.Skill {
	return appbot.Skill{
		Name: "tree",
		Hint: "Advent of Code",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/tree", bot.MatchTypePrefix, handleTree)
		},
	}
}

func handleTree(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}

	now := time.Now()
	year := now.Year()
	if now.Month() < time.December {
		year--
	}

	text := fmt.Sprintf(
		"🎄🎄🎄 Присоединяйся к ежегодному решению елки! 🎄🎄🎄 \n"+
			"👉👉👉 https://adventofcode.com/ 👈👈👈 \n"+
			"😼😼😼 VLDC leaderboard: https://adventofcode.com/%d/leaderboard/private/view/%s \n"+
			"Join Code: `458538-e2a0698b`",
		year, aocLeaderboardID,
	)

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   text,
	})
}
