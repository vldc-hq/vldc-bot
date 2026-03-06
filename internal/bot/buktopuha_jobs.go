package bot

import (
	"context"
	"fmt"
	"strings"
	"time"
)

func (r *Runtime) scheduleBuktopuhaRound(chatID int64) {
	if r.deps.BuktopuhaGame == nil || r.scheduler == nil {
		return
	}

	word, ok := r.deps.BuktopuhaGame.ActiveWord(chatID)
	if !ok || strings.TrimSpace(word) == "" {
		return
	}

	r.cancelBuktopuhaRound(chatID)

	_, _ = r.scheduler.RunOnce(r.bukHint1Job(chatID), 10*time.Second, func(ctx context.Context) {
		hint := fmt.Sprintf("buktopuha hint #1: starts with '%c'", []rune(word)[0])
		_ = r.gw.SendMessage(ctx, chatID, hint)
	})

	_, _ = r.scheduler.RunOnce(r.bukHint2Job(chatID), 20*time.Second, func(ctx context.Context) {
		hint := fmt.Sprintf("buktopuha hint #2: word length is %d", len([]rune(word)))
		_ = r.gw.SendMessage(ctx, chatID, hint)
	})

	_, _ = r.scheduler.RunOnce(r.bukEndJob(chatID), 30*time.Second, func(ctx context.Context) {
		w, still := r.deps.BuktopuhaGame.ActiveWord(chatID)
		if still {
			r.deps.BuktopuhaGame.Stop(chatID)
			_ = r.gw.SendMessage(ctx, chatID, "buktopuha round over, word was: "+w)
		}
	})
}

func (r *Runtime) cancelBuktopuhaRound(chatID int64) {
	if r.scheduler == nil {
		return
	}
	r.scheduler.Cancel(r.bukHint1Job(chatID))
	r.scheduler.Cancel(r.bukHint2Job(chatID))
	r.scheduler.Cancel(r.bukEndJob(chatID))
}

func (r *Runtime) bukHint1Job(chatID int64) string { return fmt.Sprintf("hint1-%d", chatID) }
func (r *Runtime) bukHint2Job(chatID int64) string { return fmt.Sprintf("hint2-%d", chatID) }
func (r *Runtime) bukEndJob(chatID int64) string   { return fmt.Sprintf("end-%d", chatID) }
