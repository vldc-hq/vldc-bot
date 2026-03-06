package skill

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

const (
	nastyaModeName    = "nastya_mode"
	maxVoiceDuration  = 60 // seconds
	voiceMuteDuration = 7 * 24 * time.Hour
)

var nastyaExcluded = map[string]bool{
	"ravino_doul": true,
}

func NastyaSkill() appbot.Skill {
	return appbot.Skill{
		Name: "nastya_mode",
		Hint: "voice message handler",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			deps.ModeState.Register(&mode.ModeConfig{
				Name:      nastyaModeName,
				DefaultOn: true,
			})

			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil {
					return false
				}
				msg := update.Message
				if msg.Voice == nil && msg.VideoNote == nil {
					return false
				}
				return deps.ModeState.IsEnabled(msg.Chat.ID, nastyaModeName)
			}, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleNastyaMode(ctx, b, update)
			})
		},
	}
}

func handleNastyaMode(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil || update.Message.From == nil {
		return
	}
	msg := update.Message
	user := msg.From

	// Check excluded users
	if nastyaExcluded[strings.TrimPrefix(user.Username, "@")] {
		return
	}

	var duration int
	if msg.Voice != nil {
		duration = msg.Voice.Duration
	} else if msg.VideoNote != nil {
		duration = msg.VideoNote.Duration
	}

	var text string
	if duration > maxVoiceDuration {
		text = fmt.Sprintf("🤫🤫🤫 @%s! Слишком много наговорил...", user.Username)
	} else {
		text = fmt.Sprintf(
			"🤫🤫🤫 Групповой чат — не место для войсов и кружочков, @%s!",
			user.Username,
		)
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   text,
	})

	MuteUserForDuration(ctx, b, msg.Chat.ID, user.ID, user.FirstName, voiceMuteDuration)

	_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{
		ChatID:    msg.Chat.ID,
		MessageID: msg.ID,
	})
}
