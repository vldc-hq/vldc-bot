package bot

import (
	"context"
	"testing"
)

func TestAdminOnlyCommandsBlockedForNonAdmin(t *testing.T) {
	registry, err := NewRegistry(buildCommandSpecs(Dependencies{}), RequireAdminMiddleware(func(context.Context, IncomingUpdate) (bool, error) {
		return false, nil
	}))
	if err != nil {
		t.Fatalf("new registry: %v", err)
	}

	for _, spec := range registry.Specs() {
		if !spec.RequireAdmin {
			continue
		}

		h, ok := registry.Handler(spec.Name)
		if !ok {
			t.Fatalf("handler not found for command %q", spec.Name)
		}

		tg := &fakeTG{}
		in := IncomingUpdate{
			ChatID:       100,
			UserID:       200,
			ReplyToID:    300,
			ReplyToMsgID: 10,
			MessageID:    11,
			Command:      spec.Name,
			Args:         []string{"15"},
			Text:         "some text",
		}

		if err := h(context.Background(), in, tg); err != nil {
			t.Fatalf("command %q returned error: %v", spec.Name, err)
		}

		if tgSideEffectsCount(tg) != 0 {
			t.Fatalf("expected no side effects for blocked admin command %q, got: %+v", spec.Name, tg)
		}
	}
}

func tgSideEffectsCount(tg *fakeTG) int {
	if tg == nil {
		return 0
	}
	return len(tg.messages) + len(tg.banned) + len(tg.muted) + len(tg.unbanned) + len(tg.deleted)
}
