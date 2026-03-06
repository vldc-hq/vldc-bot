package skill

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"sync"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

const (
	muteMinutesPerSlot = 16 * 60 // 16h
	numBullets         = 6
)

type rollState struct {
	mu      sync.Mutex
	barrels map[int64][]bool // chatID -> barrel
}

func newRollState() *rollState {
	return &rollState{barrels: make(map[int64][]bool)}
}

func (rs *rollState) shot(chatID int64) (isShot bool, shotsRemained int) {
	rs.mu.Lock()
	defer rs.mu.Unlock()

	barrel, ok := rs.barrels[chatID]
	if !ok || len(barrel) == 0 {
		barrel = rs.reload(chatID)
	}

	fate := barrel[len(barrel)-1]
	barrel = barrel[:len(barrel)-1]
	rs.barrels[chatID] = barrel
	shotsRemained = len(barrel)

	if fate {
		rs.reload(chatID)
	}

	isShot = fate
	return
}

func (rs *rollState) reload(chatID int64) []bool {
	barrel := make([]bool, numBullets)
	barrel[rand.IntN(numBullets)] = true
	rs.barrels[chatID] = barrel
	return barrel
}

func getMuteMinutes(shotsRemain int) int {
	return muteMinutesPerSlot * (numBullets - shotsRemain)
}

func getMissString(shotsRemain int) string {
	emojis := []string{"😕", "😟", "😥", "😫", "😱"}
	idx := numBullets - shotsRemain - 1
	if idx < 0 {
		idx = 0
	}
	if idx >= len(emojis) {
		idx = len(emojis) - 1
	}

	misses := ""
	for range numBullets - shotsRemain {
		misses += "🔘"
	}
	chances := ""
	for range shotsRemain {
		chances += "⚪️"
	}

	h := getMuteMinutes(shotsRemain-1) / 60
	return fmt.Sprintf("%s🔫 MISS! Barrel: %s%s, %dh", emojis[idx], misses, chances, h)
}

func RollSkill() appbot.Skill {
	state := newRollState()
	var database *db.DB

	return appbot.Skill{
		Name: "roll",
		Hint: "Russian roulette",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB

			b.RegisterHandler(bot.HandlerTypeMessageText, "/roll", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleRoll(ctx, b, update, state, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/gdpr_me", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleGDPR(ctx, b, update, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/hussars", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleHussars(ctx, b, update, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/htop", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleActiveHussars(ctx, b, update, database)
			})
			b.RegisterHandler(bot.HandlerTypeMessageText, "/wipe_hussars", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleWipeHussars(ctx, b, update, database)
			})
		},
	}
}

func handleRoll(ctx context.Context, b *bot.Bot, update *models.Update, state *rollState, database *db.DB) {
	if update.Message == nil {
		return
	}
	msg := update.Message
	user := msg.From
	if user == nil {
		return
	}

	// Ensure hussar exists
	existing, _ := database.FindHussar(user.ID)
	if existing == nil {
		meta, _ := json.Marshal(map[string]string{
			"username":   user.Username,
			"first_name": user.FirstName,
			"last_name":  user.LastName,
		})
		_ = database.AddHussar(user.ID, string(meta))
	}

	isShot, shotsRemained := state.shot(msg.Chat.ID)

	if isShot {
		muteMin := getMuteMinutes(shotsRemained)
		slog.Info("roll: user shot", "user", user.FirstName, "user_id", user.ID, "mute_hours", muteMin/60)

		result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("💥 boom! %s 😵 [%dh mute]", user.FirstName, muteMin/60),
		})
		util.ScheduleCleanup(b, msg.Chat.ID, 120*time.Second, msg.ID, msgID(result))

		MuteUserForDuration(ctx, b, msg.Chat.ID, user.ID, user.FirstName, time.Duration(muteMin)*time.Minute)
		_ = database.HussarDead(user.ID, muteMin)
	} else {
		slog.Info("roll: user missed", "user", user.FirstName, "user_id", user.ID)
		_ = database.HussarMiss(user.ID)

		result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   fmt.Sprintf("%s: %s", user.FirstName, getMissString(shotsRemained)),
		})
		util.ScheduleCleanup(b, msg.Chat.ID, 120*time.Second, msg.ID, msgID(result))
	}
}

func handleGDPR(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}
	user := update.Message.From
	if user == nil {
		return
	}

	_ = database.RemoveHussar(user.ID)
	slog.Info("hussar removed (GDPR)", "user", user.FirstName)

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:          update.Message.Chat.ID,
		Text:            "ok, boomer 😒",
		ReplyParameters: &models.ReplyParameters{MessageID: update.Message.ID},
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 120*time.Second, update.Message.ID, msgID(result))
}

func handleHussars(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}

	hussars, err := database.GetAllHussars()
	if err != nil {
		slog.Error("failed to get hussars", "error", err)
		return
	}

	if len(hussars) == 0 {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: update.Message.Chat.ID,
			Text:   "No hussars yet 😒",
		})
		return
	}

	board := fmt.Sprintf("%-18s | %-8s | %-6s | %s\n", "time in club", "attempts", "deaths", "hussar")
	board += "------------------ + -------- + ------ + -----------\n"
	for _, h := range hussars {
		d := time.Duration(h.TotalTimeInClub) * time.Second
		board += fmt.Sprintf("%-18s | %-8d | %-6d | %s\n",
			d.Truncate(time.Second).String(),
			h.ShotCounter,
			h.DeadCounter,
			h.Username(),
		)
	}

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:    update.Message.Chat.ID,
		Text:      fmt.Sprintf("```\n%s```", board),
		ParseMode: models.ParseModeMarkdown,
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 600*time.Second, update.Message.ID, msgID(result))
}

func handleActiveHussars(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}
	if !appbot.IsAdmin(ctx, b, update.Message.Chat.ID, update.Message.From.ID) {
		return
	}

	hussars, err := database.GetAllHussars()
	if err != nil {
		return
	}

	text := "No hussars in da club 😒"
	var restricted []db.Hussar
	for _, h := range hussars {
		member, err := b.GetChatMember(ctx, &bot.GetChatMemberParams{
			ChatID: update.Message.Chat.ID,
			UserID: h.UserID,
		})
		if err != nil {
			continue
		}
		if member.Type == "restricted" {
			restricted = append(restricted, h)
		}
	}

	if len(restricted) > 0 {
		text = "Right meow in da club ☠️:\n"
		for _, h := range restricted {
			text += fmt.Sprintf("• %s\n", h.Username())
		}
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   text,
	})
}

func handleWipeHussars(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}
	if !appbot.IsAdmin(ctx, b, update.Message.Chat.ID, update.Message.From.ID) {
		return
	}

	_ = database.RemoveAllHussars()
	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:          update.Message.Chat.ID,
		Text:            "👍",
		ReplyParameters: &models.ReplyParameters{MessageID: update.Message.ID},
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 120*time.Second, update.Message.ID, msgID(result))
}
