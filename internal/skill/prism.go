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

func PrismSkill() appbot.Skill {
	var database *db.DB

	return appbot.Skill{
		Name: "prism",
		Hint: "word frequency tracker",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB

			b.RegisterHandler(bot.HandlerTypeMessageText, "/top", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handlePrismTop(ctx, b, update, database)
			})

			// Track all messages for word frequency
			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				return update.Message != nil && update.Message.Text != "" && !strings.HasPrefix(update.Message.Text, "/")
			}, func(ctx context.Context, _ *bot.Bot, update *models.Update) {
				trackWords(update.Message.Text, database)
			})
		},
	}
}

func trackWords(text string, database *db.DB) {
	words := strings.Fields(strings.ToLower(text))
	for _, word := range words {
		word = strings.TrimFunc(word, func(r rune) bool {
			isLatin := r >= 'a' && r <= 'z'
			isCyrillic := r >= 'а' && r <= 'я' || r == 'ё'
			isDigit := r >= '0' && r <= '9'
			return !isLatin && !isCyrillic && !isDigit
		})
		if word == "" || len(word) < 2 {
			continue
		}
		_ = database.AddPrismWord(word)
	}
}

func handlePrismTop(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}

	words, err := database.GetAllPrismWords()
	if err != nil || len(words) == 0 {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: update.Message.Chat.ID,
			Text:   "No words tracked yet",
		})
		return
	}

	limit := 10
	if limit > len(words) {
		limit = len(words)
	}

	var sb strings.Builder
	sb.WriteString("Top words:\n\n")
	for i, w := range words[:limit] {
		fmt.Fprintf(&sb, "%d. %s — %d\n", i+1, w.Word, w.Count)
	}

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   sb.String(),
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 600*time.Second, update.Message.ID, msgID(result))
}
