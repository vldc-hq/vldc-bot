package bot

import (
	"context"
	"fmt"
	"time"
)

func (r *Runtime) startChatModeScheduler() {
	if r.deps.GroupChatID == "" || r.deps.Modes == nil {
		return
	}

	chatID := parseChatID(r.deps.GroupChatID)
	if chatID == 0 {
		return
	}

	_, err := r.scheduler.RunRepeating("chat_mode_tick", time.Hour, func(ctx context.Context) {
		if !r.deps.Modes.ChatOn(chatID) {
			return
		}
		if err := r.sendChatModeMessage(ctx, chatID); err != nil {
			r.logger.Warn("chat mode message failed", "error", err)
		}
	})
	if err != nil {
		r.logger.Warn("failed to start chat mode scheduler", "error", err)
	}
}

func (r *Runtime) sendChatModeMessage(ctx context.Context, chatID int64) error {
	msg := "нян задумчиво смотрит в логи и шепчет: не забудьте писать тесты"
	if r.deps.ChatGenerator != nil {
		if generated, provider, err := r.deps.ChatGenerator.Generate(ctx, "short dev reminder for group chat"); err == nil && generated != "" {
			msg = generated + " [" + provider + "]"
		} else if err != nil {
			r.logger.Debug("chat generator fallback failed", "error", err)
		}
	}

	return r.gw.SendMessage(ctx, chatID, msg)
}

func (r *Runtime) bumpBuktopuhaStats(ctx context.Context, in IncomingUpdate, score int) error {
	if r.deps.Buktopuha == nil || in.UserID == 0 {
		return nil
	}
	now := time.Now()
	item, ok, err := r.deps.Buktopuha.Get(ctx, in.UserID)
	if err != nil {
		return err
	}
	if !ok {
		meta := fmt.Sprintf(`{"user_id":%d,"username":%q,"first_name":%q,"last_name":%q}`, in.UserID, in.Username, in.FirstName, in.LastName)
		return r.deps.Buktopuha.Add(ctx, in.UserID, meta, score, now)
	}
	if score > 0 {
		return r.deps.Buktopuha.IncrementWin(ctx, item.UserID, score, now)
	}
	return r.deps.Buktopuha.IncrementGame(ctx, item.UserID, now)
}
