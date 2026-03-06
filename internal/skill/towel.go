package skill

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"strings"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

const (
	quarantineMinutes = 60
	minReplyLen       = 15
	magicCallbackData = "42"
	towelModeName     = "towel_mode"
)

var iAmBot = []string{
	"I am a bot!", "Я бот!", "私はボットです！",
	"Ma olen bot!", "मैं एक बॉट हूँ!", "Je suis un bot!",
	"Unë jam një bot!", "أنا بوت!", "אני בוט!",
	"Sono un robot!", "我是機器人！",
}

func TowelSkill() appbot.Skill {
	var database *db.DB
	var modeState *mode.State

	return appbot.Skill{
		Name: "towel_mode",
		Hint: "anti-bot quarantine",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB
			modeState = deps.ModeState

			modeState.Register(&mode.ModeConfig{
				Name:      towelModeName,
				DefaultOn: true,
				OffCallback: func() {
					_ = database.DeleteAllQuarantineUsers()
				},
			})

			// Handle new chat members
			b.RegisterHandler(bot.HandlerTypeMessageText, "", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				// This is a catch-all; we check for quarantine replies
				handleTowelReply(ctx, b, update, database, modeState)
			})

			// Handle callback query (I am a bot button)
			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				return update.CallbackQuery != nil && update.CallbackQuery.Data == magicCallbackData
			}, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleIAmBotButton(ctx, b, update, database)
			})

			// Start ban checker goroutine
			if deps.Config.GroupChatID != "" {
				go runBanChecker(b, deps, database, modeState)
			}
		},
	}
}

// RegisterNewChatMembersHandler should be called to handle new members joining.
// This is separated because the go-telegram/bot library needs specific handling for status updates.
func RegisterNewChatMembersHandler(b *bot.Bot, deps *appbot.Deps) {
	b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
		return update.Message != nil && len(update.Message.NewChatMembers) > 0
	}, func(ctx context.Context, bt *bot.Bot, update *models.Update) {
		if !deps.ModeState.IsEnabled(update.Message.Chat.ID, towelModeName) {
			return
		}
		for _, user := range update.Message.NewChatMembers {
			quarantineUser(ctx, bt, deps.DB, update.Message.Chat.ID, &user)
		}
	})
}

func quarantineUser(ctx context.Context, b *bot.Bot, database *db.DB, chatID int64, user *models.User) {
	slog.Info("quarantining user", "user", user.FirstName, "user_id", user.ID)
	_ = database.AddQuarantineUser(user.ID, quarantineMinutes)

	btnText := iAmBot[rand.IntN(len(iAmBot))]
	msg, err := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text: fmt.Sprintf(
			"%s НЕ нажимай на кнопку ниже, чтобы доказать, что ты не бот.\n"+
				"Просто ответь (reply) на это сообщение, кратко написав о себе (у нас так принято).\n"+
				"Я буду удалять твои сообщения, пока ты не сделаешь это.\n"+
				"А коли не сделаешь, через %d минут выкину из чата.\n"+
				"Ничего личного, просто боты одолели.\n",
			displayName(user), quarantineMinutes,
		),
		ReplyMarkup: &models.InlineKeyboardMarkup{
			InlineKeyboard: [][]models.InlineKeyboardButton{
				{{Text: btnText, CallbackData: magicCallbackData}},
			},
		},
	})
	if err != nil {
		slog.Error("failed to send quarantine message", "error", err)
		return
	}
	_ = database.AddQuarantineRelMessage(user.ID, msg.ID)
}

func handleTowelReply(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB, modeState *mode.State) {
	if update.Message == nil || update.Message.From == nil {
		return
	}
	msg := update.Message
	chatID := msg.Chat.ID

	if !modeState.IsEnabled(chatID, towelModeName) {
		return
	}

	userID := msg.From.ID
	qu, err := database.FindQuarantineUser(userID)
	if err != nil || qu == nil {
		return // not in quarantine
	}

	// Check if it's a reply to the bot
	if msg.ReplyToMessage != nil && msg.ReplyToMessage.From != nil {
		text := msg.Text
		if len(text) < minReplyLen {
			// Too short
			_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{ChatID: chatID, MessageID: msg.ID})
			feedback, _ := b.SendMessage(ctx, &bot.SendMessageParams{
				ChatID: chatID,
				Text:   fmt.Sprintf("%s, твой ответ слишком короткий. Я верю, что ты можешь написать больше о себе!", displayName(msg.From)),
			})
			if feedback != nil {
				_ = database.AddQuarantineRelMessage(userID, feedback.ID)
			}
			return
		}

		if IsWorthy(text) {
			// Welcome!
			deleteQuarantineMessages(ctx, b, chatID, qu)
			_ = database.DeleteQuarantineUser(userID)
			_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
				ChatID:          chatID,
				Text:            "Добро пожаловать в VLDC!",
				ReplyParameters: &models.ReplyParameters{MessageID: msg.ID},
			})
			return
		}

		// Spam detected
		_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{ChatID: chatID, MessageID: msg.ID})
		return
	}

	// Not a reply to bot — delete
	_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{ChatID: chatID, MessageID: msg.ID})
}

func handleIAmBotButton(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.CallbackQuery == nil || update.CallbackQuery.From.ID == 0 {
		return
	}

	user := update.CallbackQuery.From
	qu, _ := database.FindQuarantineUser(user.ID)

	var text string
	if qu != nil {
		text = fmt.Sprintf("%s, попробуй прочитать сообщение от бота внимательней :3", displayName(&user))
	} else {
		text = fmt.Sprintf("Любопытство сгубило кошку, %s :3", displayName(&user))
	}

	_, _ = b.AnswerCallbackQuery(ctx, &bot.AnswerCallbackQueryParams{
		CallbackQueryID: update.CallbackQuery.ID,
		Text:            text,
		ShowAlert:       true,
	})
}

func deleteQuarantineMessages(ctx context.Context, b *bot.Bot, chatID int64, qu *db.QuarantineUser) {
	for _, msgID := range qu.MessageIDs() {
		_, err := b.DeleteMessage(ctx, &bot.DeleteMessageParams{ChatID: chatID, MessageID: msgID})
		if err != nil {
			slog.Debug("failed to delete quarantine message", "msg_id", msgID, "error", err)
		}
	}
}

func runBanChecker(b *bot.Bot, deps *appbot.Deps, database *db.DB, modeState *mode.State) {
	ticker := time.NewTicker(60 * time.Second)
	defer ticker.Stop()

	for range ticker.C {
		chatID := deps.Config.ChatID()
		if chatID == 0 || !modeState.IsEnabled(chatID, towelModeName) {
			continue
		}

		users, err := database.FindAllQuarantineUsers()
		if err != nil {
			continue
		}

		ctx := context.Background()
		for _, u := range users {
			if !u.IsExpired() {
				continue
			}

			slog.Info("banning expired quarantine user", "user_id", u.UserID)
			_, err := b.BanChatMember(ctx, &bot.BanChatMemberParams{
				ChatID: chatID,
				UserID: u.UserID,
			})
			if err != nil {
				slog.Error("failed to ban user", "user_id", u.UserID, "error", err)
				continue
			}

			qu, _ := database.FindQuarantineUser(u.UserID)
			if qu != nil {
				deleteQuarantineMessages(ctx, b, chatID, qu)
			}
			_ = database.DeleteQuarantineUser(u.UserID)
		}
	}
}

// IsWorthy checks if the reply text is a legitimate bio (not spam).
// For now, implements basic checks. AI integration can be added later.
func IsWorthy(text string) bool {
	if len(text) < minReplyLen {
		return false
	}
	// Backdoor for testing (same as Python version)
	if strings.Contains(strings.ToLower(text), "i love vldc") {
		return true
	}
	// Without AI configured, allow all sufficiently long messages
	return true
}
