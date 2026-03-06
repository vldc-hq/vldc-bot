package bot

import (
	"context"
	"testing"

	"github.com/go-telegram/bot/models"
)

type fakeGateway struct {
	messages []string
}

func (f *fakeGateway) SendMessage(_ context.Context, _ int64, text string) error {
	f.messages = append(f.messages, text)
	return nil
}

func (f *fakeGateway) SendMessageWithID(_ context.Context, _ int64, text string) (int, error) {
	f.messages = append(f.messages, text)
	return len(f.messages), nil
}

func (f *fakeGateway) BanChatMember(context.Context, int64, int64) error { return nil }
func (f *fakeGateway) RestrictChatMember(context.Context, int64, int64, int) error {
	return nil
}
func (f *fakeGateway) UnbanChatMember(context.Context, int64, int64) error { return nil }
func (f *fakeGateway) DeleteMessage(context.Context, int64, int) error     { return nil }

func TestRegistryRequireAdminMiddleware(t *testing.T) {
	called := false

	registry, err := NewRegistry([]CommandSpec{
		{
			Name:         "admin_only",
			RequireAdmin: true,
			Handler: func(context.Context, IncomingUpdate, TelegramGateway) error {
				called = true
				return nil
			},
		},
	}, RequireAdminMiddleware(func(context.Context, IncomingUpdate) (bool, error) {
		return false, nil
	}))
	if err != nil {
		t.Fatalf("new registry: %v", err)
	}

	h, ok := registry.Handler("admin_only")
	if !ok {
		t.Fatalf("handler not found")
	}

	if err := h(context.Background(), IncomingUpdate{Command: "admin_only"}, &fakeGateway{}); err != nil {
		t.Fatalf("handler call: %v", err)
	}

	if called {
		t.Fatalf("handler should not be called when user is not admin")
	}
}

func TestRegistrySpecDefaultsDescription(t *testing.T) {
	registry, err := NewRegistry([]CommandSpec{{Name: "ping", Handler: func(context.Context, IncomingUpdate, TelegramGateway) error { return nil }}})
	if err != nil {
		t.Fatalf("new registry: %v", err)
	}

	specs := registry.Specs()
	if len(specs) != 1 {
		t.Fatalf("unexpected specs length: %d", len(specs))
	}
	if specs[0].Description != "ping" {
		t.Fatalf("expected default description to match command name, got %q", specs[0].Description)
	}
}

func TestParseIncomingUpdateExtractsCommand(t *testing.T) {
	update := &models.Update{
		Message: &models.Message{
			ID:   123,
			Text: "/Start@vldc_bot hello",
			Chat: models.Chat{ID: 777},
			From: &models.User{ID: 42, Username: "u", FirstName: "f", LastName: "l"},
			ReplyToMessage: &models.Message{
				ID:   22,
				From: &models.User{ID: 99},
			},
			Voice:     &models.Voice{FileID: "v"},
			VideoNote: &models.VideoNote{FileID: "n"},
		},
	}

	parsed := parseIncomingUpdate(update)

	if parsed.Command != "start" {
		t.Fatalf("unexpected command: got=%q want=%q", parsed.Command, "start")
	}
	if parsed.ChatID != 777 || parsed.UserID != 42 || parsed.MessageID != 123 {
		t.Fatalf("unexpected parsed ids: chat=%d user=%d msg=%d", parsed.ChatID, parsed.UserID, parsed.MessageID)
	}
	if parsed.ReplyToID != 99 || parsed.ReplyToMsgID != 22 {
		t.Fatalf("unexpected reply parse: reply_user=%d reply_msg=%d", parsed.ReplyToID, parsed.ReplyToMsgID)
	}
	if !parsed.HasVoice || !parsed.HasVideoNote {
		t.Fatalf("expected media flags to be set")
	}
}
