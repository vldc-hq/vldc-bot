package bot

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"strings"
	"time"

	tgbot "github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func (r *Runtime) routeDefault(ctx context.Context, _ *tgbot.Bot, upd *models.Update) {
	if upd == nil || upd.Message == nil {
		return
	}

	in := parseIncomingUpdate(upd)
	r.handleNonTextPolicies(ctx, in)
}

func (r *Runtime) handleNonTextPolicies(ctx context.Context, in IncomingUpdate) {
	r.handleTowelMode(ctx, in)
	r.handleNastyaMode(ctx, in)
	r.handleFoolsMode(ctx, in)
}

func (r *Runtime) handleTowelMode(ctx context.Context, in IncomingUpdate) {
	if r.deps.Modes == nil || !r.deps.Modes.TowelOn(in.ChatID) || r.deps.Quarantine == nil {
		return
	}

	now := time.Now()
	for _, userID := range in.NewMembers {
		if userID == 0 {
			continue
		}
		if err := r.deps.Quarantine.Add(ctx, userID, now.Add(60*time.Minute)); err != nil {
			r.logger.Warn("failed to add quarantine user", "user_id", userID, "error", err)
			continue
		}

		prompt := fmt.Sprintf("user %d, reply with short intro (>=15 chars) in 60 minutes or you will be banned", userID)
		msgID, err := r.gw.SendMessageWithID(ctx, in.ChatID, prompt)
		if err != nil {
			r.logger.Warn("failed to send quarantine prompt", "user_id", userID, "error", err)
		} else {
			if addErr := r.deps.Quarantine.AddRelatedMessage(ctx, userID, int64(msgID)); addErr != nil {
				r.logger.Warn("failed to add quarantine related message", "user_id", userID, "error", addErr)
			}
		}
	}

	if in.UserID == 0 {
		return
	}

	qu, ok, err := r.deps.Quarantine.Get(ctx, in.UserID)
	if err != nil {
		r.logger.Warn("failed to load quarantine user", "user_id", in.UserID, "error", err)
		return
	}
	if !ok {
		return
	}

	if time.Now().After(qu.Until) {
		if err := r.gw.BanChatMember(ctx, in.ChatID, in.UserID); err != nil {
			r.logger.Warn("failed to ban expired quarantine user", "user_id", in.UserID, "error", err)
		} else {
			_ = r.deps.Quarantine.Delete(ctx, in.UserID)
		}
		return
	}

	if in.ReplyToMsgID != 0 && len(strings.TrimSpace(in.Text)) >= 15 {
		if allowedReplyTo(qu.RelMessages, in.ReplyToMsgID) {
			if r.deps.BioChecker != nil && !r.deps.BioChecker.IsWorthyBio(in.Text) {
				if in.MessageID != 0 {
					_ = r.gw.DeleteMessage(ctx, in.ChatID, in.MessageID)
				}
				_ = r.gw.SendMessage(ctx, in.ChatID, "your intro looks like spam, please try again")
				return
			}

			_ = r.deps.Quarantine.Delete(ctx, in.UserID)
			_ = r.gw.SendMessage(ctx, in.ChatID, fmt.Sprintf("welcome, user %d", in.UserID))
			return
		}
	}

	if in.MessageID != 0 {
		_ = r.gw.DeleteMessage(ctx, in.ChatID, in.MessageID)
	}
}

func (r *Runtime) handleNastyaMode(ctx context.Context, in IncomingUpdate) {
	if r.deps.Modes == nil || !r.deps.Modes.NastyaOn(in.ChatID) {
		return
	}
	if !in.HasVoice && !in.HasVideoNote {
		return
	}

	if in.UserID != 0 {
		_ = r.gw.RestrictChatMember(ctx, in.ChatID, in.UserID, 7*24*60)
	}
	if in.MessageID != 0 {
		_ = r.gw.DeleteMessage(ctx, in.ChatID, in.MessageID)
	}
	base := fmt.Sprintf("@%s voice/video is disabled in this chat", in.Username)
	if r.deps.Speech != nil {
		if text, err := r.deps.Speech.Recognize(ctx, ""); err == nil && strings.TrimSpace(text) != "" {
			base += "\nrecognized: " + text
		}
	}
	_ = r.gw.SendMessage(ctx, in.ChatID, base)
}

func (r *Runtime) handleFoolsMode(ctx context.Context, in IncomingUpdate) {
	if r.deps.Modes == nil || !r.deps.Modes.FoolsOn(in.ChatID) {
		return
	}
	if in.Text == "" || strings.HasPrefix(in.Text, "/") {
		return
	}

	transformed := foolsTransform(in.Text)
	if r.deps.Translator != nil {
		langs := []string{"ro", "uk", "sr", "sk", "sl", "uz", "bg", "mn", "kk"}
		target := langs[int(in.UserID)%len(langs)]
		if translated, err := r.deps.Translator.Translate(ctx, in.Text, "ru", target); err == nil && strings.TrimSpace(translated) != "" {
			transformed = translated
		} else {
			_ = err
		}
	}
	if transformed == in.Text {
		return
	}
	if in.MessageID != 0 {
		_ = r.gw.DeleteMessage(ctx, in.ChatID, in.MessageID)
	}
	_ = r.gw.SendMessage(ctx, in.ChatID, fmt.Sprintf("%s: %s", displayName(in), transformed))
}

func displayName(in IncomingUpdate) string {
	if in.Username != "" {
		return "@" + in.Username
	}
	full := strings.TrimSpace(strings.Join([]string{in.FirstName, in.LastName}, " "))
	if full != "" {
		return full
	}
	return fmt.Sprintf("user-%d", in.UserID)
}

func foolsTransform(s string) string {
	repl := strings.NewReplacer(
		"а", "я", "о", "а", "у", "ю", "ы", "и", "э", "е",
		"А", "Я", "О", "А", "У", "Ю", "Ы", "И", "Э", "Е",
	)
	res := repl.Replace(s)
	if res == s {
		r := []rune(s)
		if len(r) > 2 {
			i := rand.Intn(len(r))
			r[i] = '!'
			res = string(r)
		}
	}
	return res
}

func allowedReplyTo(raw string, msgID int) bool {
	if msgID == 0 {
		return false
	}
	if strings.TrimSpace(raw) == "" || raw == "[]" {
		return true
	}
	var ids []int64
	if err := json.Unmarshal([]byte(raw), &ids); err != nil {
		return false
	}
	for _, id := range ids {
		if int64(msgID) == id {
			return true
		}
	}
	return false
}
