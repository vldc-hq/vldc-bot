package bot

import "context"

type IncomingUpdate struct {
	ChatID       int64
	UserID       int64
	Username     string
	FirstName    string
	LastName     string
	ReplyToID    int64
	ReplyToMsgID int
	MessageID    int
	Text         string
	Command      string
	Args         []string
	HasSticker   bool
	HasAnimation bool
	HasVoice     bool
	HasVideoNote bool
	NewMembers   []int64
}

type TelegramGateway interface {
	SendMessage(ctx context.Context, chatID int64, text string) error
	SendMessageWithID(ctx context.Context, chatID int64, text string) (int, error)
	BanChatMember(ctx context.Context, chatID int64, userID int64) error
	RestrictChatMember(ctx context.Context, chatID int64, userID int64, minutes int) error
	UnbanChatMember(ctx context.Context, chatID int64, userID int64) error
	DeleteMessage(ctx context.Context, chatID int64, messageID int) error
}

type CommandHandler func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error
