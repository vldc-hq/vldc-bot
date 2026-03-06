package skill

import (
	"context"
	"fmt"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

func BanSkill() appbot.Skill {
	return appbot.Skill{
		Name: "ban",
		Hint: "ban users",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/ban", bot.MatchTypePrefix, handleBan)
		},
	}
}

func handleBan(ctx context.Context, b *bot.Bot, update *models.Update) {
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

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("Пользователь %s был забанен", displayName(target)),
	})
	util.ScheduleCleanup(b, msg.Chat.ID, 600*time.Second, msg.ID, msgID(result))
}
