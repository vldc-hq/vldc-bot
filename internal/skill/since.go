package skill

import (
	"context"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

const sinceModeName = "since_mode"

func SinceSkill() appbot.Skill {
	var database *db.DB

	return appbot.Skill{
		Name: "since_mode",
		Hint: "topic discussion tracker",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB

			deps.ModeState.Register(&mode.ModeConfig{
				Name:      sinceModeName,
				DefaultOn: false,
			})

			b.RegisterHandler(bot.HandlerTypeMessageText, "/since_list", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleSinceList(ctx, b, update, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/since", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleSince(ctx, b, update, database, deps.ModeState)
			})
		},
	}
}

func handleSince(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB, modeState *mode.State) {
	if update.Message == nil {
		return
	}
	msg := update.Message

	if !modeState.IsEnabled(msg.Chat.ID, sinceModeName) {
		return
	}

	topic := extractArgs(msg.Text, "/since")
	if topic == "" {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   "Usage: /since <topic>",
		})
		return
	}

	topic = strings.ToLower(topic)

	existing, _ := database.GetSinceTopic(topic)
	_ = database.UpsertSinceTopic(topic)

	var daysSince int
	if existing != nil {
		t, err := time.Parse(time.RFC3339, existing.SinceDatetime)
		if err == nil {
			daysSince = int(time.Since(t).Hours() / 24)
		}
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("%d days without «%s»! Already discussed %d times", daysSince, topic, existing.Count+1),
		})
	} else {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("0 days without «%s»! First time discussing this!", topic),
		})
	}
}

func handleSinceList(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}

	topics, err := database.GetAllSinceTopics(20)
	if err != nil {
		slog.Error("failed to get since topics", "error", err)
		return
	}

	if len(topics) == 0 {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: update.Message.Chat.ID,
			Text:   "No topics yet",
		})
		return
	}

	text := "Hot topics:\n\n"
	for i, t := range topics {
		text += fmt.Sprintf("%d. %s (%d times)\n", i+1, t.Topic, t.Count)
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   text,
	})
}
