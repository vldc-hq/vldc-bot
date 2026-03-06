package bot

import (
	"context"
	"time"
)

func (r *Runtime) startTowelCleanupScheduler() {
	if r.deps.Quarantine == nil || r.deps.Modes == nil || r.deps.GroupChatID == "" {
		return
	}

	chatID := parseChatID(r.deps.GroupChatID)
	if chatID == 0 {
		return
	}

	_, err := r.scheduler.RunRepeating("towel_quarantine_cleanup", time.Minute, func(ctx context.Context) {
		if !r.deps.Modes.TowelOn(chatID) {
			return
		}

		items, listErr := r.deps.Quarantine.ListAll(ctx)
		if listErr != nil {
			r.logger.Warn("quarantine cleanup list failed", "error", listErr)
			return
		}

		now := time.Now()
		for _, item := range items {
			if now.Before(item.Until) {
				continue
			}
			if banErr := r.gw.BanChatMember(ctx, chatID, item.UserID); banErr != nil {
				r.logger.Warn("quarantine cleanup ban failed", "user_id", item.UserID, "error", banErr)
				continue
			}
			_ = r.deps.Quarantine.Delete(ctx, item.UserID)
		}
	})
	if err != nil {
		r.logger.Warn("failed to start towel cleanup job", "error", err)
	}
}
