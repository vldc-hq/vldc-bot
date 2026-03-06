package bot

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	tgbot "github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

func TestAdapterProcessUpdateDeterministic(t *testing.T) {
	var called atomic.Bool

	b, err := tgbot.New(
		"TEST_TOKEN",
		tgbot.WithSkipGetMe(),
		tgbot.WithNotAsyncHandlers(),
	)
	if err != nil {
		t.Fatalf("new bot: %v", err)
	}

	b.RegisterHandler(tgbot.HandlerTypeMessageText, "/start", tgbot.MatchTypePrefix, func(context.Context, *tgbot.Bot, *models.Update) {
		called.Store(true)
	})

	b.ProcessUpdate(context.Background(), &models.Update{
		ID: 1,
		Message: &models.Message{
			ID:   10,
			Text: "/start",
			Chat: models.Chat{ID: 1001},
		},
	})

	if !called.Load() {
		t.Fatalf("expected handler to be called")
	}
}

func TestAdapterOutgoingSendMessagePayload(t *testing.T) {
	requestSeen := make(chan string, 1)

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "/sendMessage") {
			body, _ := io.ReadAll(r.Body)
			requestSeen <- string(body)
			_, _ = w.Write([]byte(`{"ok":true,"result":{"message_id":1,"date":1,"chat":{"id":1001,"type":"private"},"text":"ok"}}`))
			return
		}

		_, _ = w.Write([]byte(`{"ok":true,"result":{"id":1,"is_bot":true,"first_name":"t","username":"t"}}`))
	}))
	defer srv.Close()

	b, err := tgbot.New(
		"TEST_TOKEN",
		tgbot.WithServerURL(srv.URL),
		tgbot.WithSkipGetMe(),
		tgbot.WithHTTPClient(5*time.Second, &http.Client{Timeout: 5 * time.Second}),
	)
	if err != nil {
		t.Fatalf("new bot: %v", err)
	}

	g := newGateway(b)
	if err := g.SendMessage(context.Background(), 1001, "hello from test"); err != nil {
		t.Fatalf("send message: %v", err)
	}

	select {
	case payload := <-requestSeen:
		if !strings.Contains(payload, `name="chat_id"`) {
			t.Fatalf("chat_id missing in payload: %s", payload)
		}
		if !strings.Contains(payload, "1001") {
			t.Fatalf("chat_id missing in payload: %s", payload)
		}
		if !strings.Contains(payload, `name="text"`) {
			t.Fatalf("text field missing in payload: %s", payload)
		}
		if !strings.Contains(payload, "hello from test") {
			t.Fatalf("text missing in payload: %s", payload)
		}
	case <-time.After(time.Second):
		t.Fatalf("timeout waiting for sendMessage request")
	}
}
