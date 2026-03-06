package skill

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

func LengthSkill() appbot.Skill {
	var database *db.DB

	return appbot.Skill{
		Name: "length",
		Hint: "user ID length tracker",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB

			b.RegisterHandler(bot.HandlerTypeMessageText, "/length", bot.MatchTypeExact, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleLength(ctx, b, update, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/longest", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleLongest(ctx, b, update, database)
			})
		},
	}
}

func handleLength(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil || update.Message.From == nil {
		return
	}
	user := update.Message.From
	idStr := fmt.Sprintf("%d", user.ID)
	length := len(idStr)

	_ = database.UpsertLengthUser(user.ID, user.Username, user.FirstName, user.LastName, length)

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:          update.Message.Chat.ID,
		Text:            fmt.Sprintf("Your telegram id length is %d 🍆 (%d)", length, user.ID),
		ReplyParameters: &models.ReplyParameters{MessageID: update.Message.ID},
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 120*time.Second, update.Message.ID, msgID(result))
}

func handleLongest(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}

	users, err := database.GetTopLengthUsers(10)
	if err != nil || len(users) == 0 {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: update.Message.Chat.ID,
			Text:   "No measurements yet 📏",
		})
		return
	}

	var sb strings.Builder
	sb.WriteString("🍆 🔝🔟 best known lengths 🍆: \n\n")
	for i, u := range users {
		fmt.Fprintf(&sb, "%d → %s\n", i+1, u.DisplayName())
	}

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   sb.String(),
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 120*time.Second, update.Message.ID, msgID(result))
}
