package skill

import (
	"context"
	"fmt"
	"strings"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

// ModeCommandsSkill registers generic /<mode>_on, /<mode>_off, /<mode> commands
// for all registered modes.
func ModeCommandsSkill(modeNames []string) appbot.Skill {
	return appbot.Skill{
		Name: "mode_commands",
		Hint: "toggle modes on/off",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			for _, name := range modeNames {
				modeName := name // capture
				// /<mode>_on
				b.RegisterHandler(bot.HandlerTypeMessageText, "/"+modeName+"_on", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
					handleModeOn(ctx, b, update, deps.ModeState, modeName)
				})
				// /<mode>_off
				b.RegisterHandler(bot.HandlerTypeMessageText, "/"+modeName+"_off", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
					handleModeOff(ctx, b, update, deps.ModeState, modeName)
				})
				// /<mode> (status)
				if !strings.Contains(modeName, "_mode") {
					continue
				}
				b.RegisterHandler(bot.HandlerTypeMessageText, "/"+modeName, bot.MatchTypeExact, func(ctx context.Context, b *bot.Bot, update *models.Update) {
					handleModeStatus(ctx, b, update, deps.ModeState, modeName)
				})
			}
		},
	}
}

func handleModeOn(ctx context.Context, b *bot.Bot, update *models.Update, modeState *mode.State, modeName string) {
	if update.Message == nil {
		return
	}
	msg := update.Message
	if !appbot.IsAdmin(ctx, b, msg.Chat.ID, msg.From.ID) {
		return
	}

	if modeState.IsEnabled(msg.Chat.ID, modeName) {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("%s is already ON", modeName),
		})
		return
	}

	_ = modeState.SetEnabled(msg.Chat.ID, modeName, true)
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("%s is ON", modeName),
	})
}

func handleModeOff(ctx context.Context, b *bot.Bot, update *models.Update, modeState *mode.State, modeName string) {
	if update.Message == nil {
		return
	}
	msg := update.Message
	if !appbot.IsAdmin(ctx, b, msg.Chat.ID, msg.From.ID) {
		return
	}

	if !modeState.IsEnabled(msg.Chat.ID, modeName) {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("%s is already OFF", modeName),
		})
		return
	}

	_ = modeState.SetEnabled(msg.Chat.ID, modeName, false)
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("%s is OFF", modeName),
	})
}

func handleModeStatus(ctx context.Context, b *bot.Bot, update *models.Update, modeState *mode.State, modeName string) {
	if update.Message == nil {
		return
	}
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   modeState.StatusText(update.Message.Chat.ID, modeName),
	})
}
