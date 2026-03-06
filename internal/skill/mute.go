package skill

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

const defaultCleanupDelay = 600 * time.Second

const (
	minMuteTime = time.Minute
	maxMuteTime = 365 * 24 * time.Hour
)

var selfMuteMessages = []string{
	"Да как эта штука работает вообще, %s?",
	"Не озоруй, %s, мало ли кто увидит",
	"Зловив %s на вила!",
	"Насилие порождает насилие, %s",
	"Опять ты, %s!",
}

func MuteSkill() appbot.Skill {
	return appbot.Skill{
		Name: "mute",
		Hint: "mute/unmute users",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/mute", bot.MatchTypePrefix, handleMute)
			b.RegisterHandler(bot.HandlerTypeMessageText, "/unmute", bot.MatchTypePrefix, handleUnmute)
		},
	}
}

func handleMute(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	msg := update.Message

	// Self-mute: /mute without reply
	if msg.ReplyToMessage == nil {
		user := msg.From
		if user == nil {
			return
		}
		MuteUserForDuration(ctx, b, msg.Chat.ID, user.ID, user.FirstName, 24*time.Hour)
		text := fmt.Sprintf(selfMuteMessages[rand.IntN(len(selfMuteMessages))], displayName(user))
		result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID:          msg.Chat.ID,
			Text:            text,
			ReplyParameters: &models.ReplyParameters{MessageID: msg.ID},
		})
		util.ScheduleCleanup(b, msg.Chat.ID, defaultCleanupDelay, msg.ID, msgID(result))
		return
	}

	// Admin mute: /mute [duration] as reply
	if !appbot.IsAdmin(ctx, b, msg.Chat.ID, msg.From.ID) {
		return
	}

	target := msg.ReplyToMessage.From
	if target == nil {
		return
	}

	args := extractArgs(msg.Text, "/mute")
	if args == "" {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID:          msg.Chat.ID,
			Text:            "Usage: /mute <duration> (e.g., /mute 90, /mute 2h30m)",
			ReplyParameters: &models.ReplyParameters{MessageID: msg.ID},
		})
		return
	}

	duration := util.ParseDuration(args)
	if duration <= 0 {
		duration = time.Minute
	}

	MuteUserForDuration(ctx, b, msg.Chat.ID, target.ID, target.FirstName, duration)
}

func handleUnmute(ctx context.Context, b *bot.Bot, update *models.Update) {
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

	UnmuteUser(ctx, b, msg.Chat.ID, target.ID, target.FirstName)
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:          msg.Chat.ID,
		Text:            fmt.Sprintf("%s, не озоруй! Мало ли кто увидит 🧐", target.FirstName),
		ReplyParameters: &models.ReplyParameters{MessageID: msg.ID},
	})
}

// MuteUserForDuration restricts a user in the chat for the given duration.
func MuteUserForDuration(ctx context.Context, b *bot.Bot, chatID, userID int64, userName string, duration time.Duration) {
	duration = max(duration, minMuteTime)
	duration = min(duration, maxMuteTime)
	until := time.Now().Add(duration)

	slog.Info("muting user", "user", userName, "user_id", userID, "duration", duration)

	_, err := b.RestrictChatMember(ctx, &bot.RestrictChatMemberParams{
		ChatID:    chatID,
		UserID:    userID,
		UntilDate: int(until.Unix()),
		Permissions: &models.ChatPermissions{
			CanSendMessages:       false,
			CanSendAudios:         false,
			CanSendDocuments:      false,
			CanSendPhotos:         false,
			CanSendVideos:         false,
			CanSendVideoNotes:     false,
			CanSendVoiceNotes:     false,
			CanSendPolls:          false,
			CanSendOtherMessages:  false,
			CanAddWebPagePreviews: false,
		},
	})
	if err != nil {
		slog.Error("failed to mute user", "user", userName, "error", err)
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: chatID,
			Text:   fmt.Sprintf("😿 не вышло, потому что: \n\n%s", err),
		})
		return
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text:   fmt.Sprintf("Таймаут для %s на %s", userName, duration),
	})
}

// UnmuteUser restores all permissions for a user.
func UnmuteUser(ctx context.Context, b *bot.Bot, chatID, userID int64, userName string) {
	slog.Info("unmuting user", "user", userName, "user_id", userID)

	_, err := b.RestrictChatMember(ctx, &bot.RestrictChatMemberParams{
		ChatID: chatID,
		UserID: userID,
		Permissions: &models.ChatPermissions{
			CanSendMessages:       true,
			CanSendAudios:         true,
			CanSendDocuments:      true,
			CanSendPhotos:         true,
			CanSendVideos:         true,
			CanSendVideoNotes:     true,
			CanSendVoiceNotes:     true,
			CanSendPolls:          true,
			CanSendOtherMessages:  true,
			CanAddWebPagePreviews: true,
			CanInviteUsers:        true,
		},
	})
	if err != nil {
		slog.Error("failed to unmute user", "user", userName, "error", err)
	}
}

func msgID(m *models.Message) int {
	if m == nil {
		return 0
	}
	return m.ID
}

func displayName(user *models.User) string {
	if user.Username != "" {
		return "@" + user.Username
	}
	return user.FirstName
}

func extractArgs(text, command string) string {
	if len(text) <= len(command) {
		return ""
	}
	rest := text[len(command):]
	if rest != "" && rest[0] == '@' {
		// strip @botname
		idx := 0
		for idx < len(rest) && rest[idx] != ' ' {
			idx++
		}
		rest = rest[idx:]
	}
	if rest != "" && rest[0] == ' ' {
		rest = rest[1:]
	}
	return rest
}
