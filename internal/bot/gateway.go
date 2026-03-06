package bot

import (
	"context"
	"fmt"
	"time"

	tgbot "github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

type gateway struct {
	bot *tgbot.Bot
}

func newGateway(bot *tgbot.Bot) TelegramGateway {
	return &gateway{bot: bot}
}

func (g *gateway) SendMessage(ctx context.Context, chatID int64, text string) error {
	_, err := g.bot.SendMessage(ctx, &tgbot.SendMessageParams{
		ChatID: chatID,
		Text:   text,
	})
	if err != nil {
		return fmt.Errorf("send telegram message: %w", err)
	}

	return nil
}

func (g *gateway) SendMessageWithID(ctx context.Context, chatID int64, text string) (int, error) {
	msg, err := g.bot.SendMessage(ctx, &tgbot.SendMessageParams{
		ChatID: chatID,
		Text:   text,
	})
	if err != nil {
		return 0, fmt.Errorf("send telegram message: %w", err)
	}

	return msg.ID, nil
}

func (g *gateway) BanChatMember(ctx context.Context, chatID int64, userID int64) error {
	_, err := g.bot.BanChatMember(ctx, &tgbot.BanChatMemberParams{
		ChatID:         chatID,
		UserID:         userID,
		RevokeMessages: false,
	})
	if err != nil {
		return fmt.Errorf("ban chat member: %w", err)
	}

	return nil
}

func (g *gateway) RestrictChatMember(ctx context.Context, chatID int64, userID int64, minutes int) error {
	if minutes < 1 {
		minutes = 1
	}

	until := int(time.Now().Add(time.Duration(minutes) * time.Minute).Unix())
	_, err := g.bot.RestrictChatMember(ctx, &tgbot.RestrictChatMemberParams{
		ChatID: chatID,
		UserID: userID,
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
		UntilDate: until,
	})
	if err != nil {
		return fmt.Errorf("restrict chat member: %w", err)
	}

	return nil
}

func (g *gateway) UnbanChatMember(ctx context.Context, chatID int64, userID int64) error {
	_, err := g.bot.UnbanChatMember(ctx, &tgbot.UnbanChatMemberParams{ChatID: chatID, UserID: userID, OnlyIfBanned: false})
	if err != nil {
		return fmt.Errorf("unban chat member: %w", err)
	}

	return nil
}

func (g *gateway) DeleteMessage(ctx context.Context, chatID int64, messageID int) error {
	_, err := g.bot.DeleteMessage(ctx, &tgbot.DeleteMessageParams{ChatID: chatID, MessageID: messageID})
	if err != nil {
		return fmt.Errorf("delete message: %w", err)
	}

	return nil
}
