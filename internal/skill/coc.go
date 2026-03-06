package skill

import (
	"context"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

func CocSkill() appbot.Skill {
	return appbot.Skill{
		Name: "coc",
		Hint: "Code of Conduct",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/coc", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				if update.Message == nil {
					return
				}
				result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
					ChatID: update.Message.Chat.ID,
					Text:   "Please behave! https://devfest.gdgvl.ru/ru/code-of-conduct/",
				})
				util.ScheduleCleanup(b, update.Message.Chat.ID, 600*time.Second, update.Message.ID, msgID(result))
			})
		},
	}
}
