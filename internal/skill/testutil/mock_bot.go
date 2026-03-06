package testutil

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
)

// MockTelegram simulates the Telegram Bot API for integration tests.
type MockTelegram struct {
	Server *httptest.Server

	mu              sync.Mutex
	sentMessages    []SentMessage
	deletedMessages []DeletedMessage
	restrictions    []Restriction
	bans            []int64
	callbacks       []AnsweredCallback
	adminUsers      map[int64]bool
}

type SentMessage struct {
	ChatID  int64
	Text    string
	ReplyTo int
}

type DeletedMessage struct {
	ChatID    int64
	MessageID int
}

type Restriction struct {
	ChatID int64
	UserID int64
	Until  int
}

type AnsweredCallback struct {
	CallbackQueryID string
	Text            string
	ShowAlert       bool
}

// formValue extracts a field from multipart or form-encoded request.
func formValue(r *http.Request, key string) string {
	_ = r.ParseMultipartForm(10 << 20)
	if r.MultipartForm != nil {
		if vals, ok := r.MultipartForm.Value[key]; ok && len(vals) > 0 {
			return vals[0]
		}
	}
	return r.FormValue(key)
}

func NewMockTelegram() *MockTelegram {
	mt := &MockTelegram{
		adminUsers: make(map[int64]bool),
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/bottest-token/getMe", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, models.User{
			ID:        999,
			IsBot:     true,
			FirstName: "TestBot",
			Username:  "test_bot",
		})
	})
	mux.HandleFunc("/bottest-token/getUpdates", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, []any{})
	})
	mux.HandleFunc("/bottest-token/setMyCommands", func(w http.ResponseWriter, _ *http.Request) {
		respondJSON(w, true)
	})
	mux.HandleFunc("/bottest-token/sendMessage", func(w http.ResponseWriter, r *http.Request) {
		mt.handleSendMessage(w, r)
	})
	mux.HandleFunc("/bottest-token/deleteMessage", func(w http.ResponseWriter, r *http.Request) {
		mt.handleDeleteMessage(w, r)
	})
	mux.HandleFunc("/bottest-token/restrictChatMember", func(w http.ResponseWriter, r *http.Request) {
		mt.handleRestrictChatMember(w, r)
	})
	mux.HandleFunc("/bottest-token/banChatMember", func(w http.ResponseWriter, r *http.Request) {
		mt.handleBanChatMember(w, r)
	})
	mux.HandleFunc("/bottest-token/getChatMember", func(w http.ResponseWriter, r *http.Request) {
		mt.handleGetChatMember(w, r)
	})
	mux.HandleFunc("/bottest-token/answerCallbackQuery", func(w http.ResponseWriter, r *http.Request) {
		mt.handleAnswerCallbackQuery(w, r)
	})

	mt.Server = httptest.NewServer(mux)
	return mt
}

func (mt *MockTelegram) Close() {
	mt.Server.Close()
}

func (mt *MockTelegram) SetAdmin(userID int64) {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	mt.adminUsers[userID] = true
}

func (mt *MockTelegram) SentMessages() []SentMessage {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	return append([]SentMessage{}, mt.sentMessages...)
}

func (mt *MockTelegram) DeletedMessages() []DeletedMessage {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	return append([]DeletedMessage{}, mt.deletedMessages...)
}

func (mt *MockTelegram) Restrictions() []Restriction {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	return append([]Restriction{}, mt.restrictions...)
}

func (mt *MockTelegram) Bans() []int64 {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	return append([]int64{}, mt.bans...)
}

func (mt *MockTelegram) AnsweredCallbacks() []AnsweredCallback {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	return append([]AnsweredCallback{}, mt.callbacks...)
}

func (mt *MockTelegram) Reset() {
	mt.mu.Lock()
	defer mt.mu.Unlock()
	mt.sentMessages = nil
	mt.deletedMessages = nil
	mt.restrictions = nil
	mt.bans = nil
	mt.callbacks = nil
}

func (mt *MockTelegram) NewBot() *bot.Bot {
	b, _ := bot.New("test-token",
		bot.WithServerURL(mt.Server.URL),
		bot.WithDefaultHandler(func(_ context.Context, _ *bot.Bot, _ *models.Update) {}),
	)
	return b
}

func (mt *MockTelegram) handleSendMessage(w http.ResponseWriter, r *http.Request) {
	var chatID int64
	fmt.Sscanf(formValue(r, "chat_id"), "%d", &chatID)
	text := formValue(r, "text")

	mt.mu.Lock()
	msgCount := len(mt.sentMessages) + 1
	mt.sentMessages = append(mt.sentMessages, SentMessage{ChatID: chatID, Text: text})
	mt.mu.Unlock()

	respondJSON(w, models.Message{
		ID:   msgCount,
		Chat: models.Chat{ID: chatID},
		Text: text,
	})
}

func (mt *MockTelegram) handleDeleteMessage(w http.ResponseWriter, r *http.Request) {
	var chatID int64
	var msgID int
	fmt.Sscanf(formValue(r, "chat_id"), "%d", &chatID)
	fmt.Sscanf(formValue(r, "message_id"), "%d", &msgID)

	mt.mu.Lock()
	mt.deletedMessages = append(mt.deletedMessages, DeletedMessage{ChatID: chatID, MessageID: msgID})
	mt.mu.Unlock()

	respondJSON(w, true)
}

func (mt *MockTelegram) handleRestrictChatMember(w http.ResponseWriter, r *http.Request) {
	var chatID int64
	var userID int64
	var until int
	fmt.Sscanf(formValue(r, "chat_id"), "%d", &chatID)
	fmt.Sscanf(formValue(r, "user_id"), "%d", &userID)
	fmt.Sscanf(formValue(r, "until_date"), "%d", &until)

	mt.mu.Lock()
	mt.restrictions = append(mt.restrictions, Restriction{ChatID: chatID, UserID: userID, Until: until})
	mt.mu.Unlock()

	respondJSON(w, true)
}

func (mt *MockTelegram) handleBanChatMember(w http.ResponseWriter, r *http.Request) {
	var userID int64
	fmt.Sscanf(formValue(r, "user_id"), "%d", &userID)

	mt.mu.Lock()
	mt.bans = append(mt.bans, userID)
	mt.mu.Unlock()

	respondJSON(w, true)
}

func (mt *MockTelegram) handleGetChatMember(w http.ResponseWriter, r *http.Request) {
	var userID int64
	fmt.Sscanf(formValue(r, "user_id"), "%d", &userID)

	mt.mu.Lock()
	isAdmin := mt.adminUsers[userID]
	mt.mu.Unlock()

	memberType := "member"
	if isAdmin {
		memberType = "administrator"
	}

	respondJSON(w, map[string]any{
		"status": memberType,
		"user": map[string]any{
			"id":         userID,
			"is_bot":     false,
			"first_name": "TestUser",
		},
	})
}

func (mt *MockTelegram) handleAnswerCallbackQuery(w http.ResponseWriter, r *http.Request) {
	mt.mu.Lock()
	mt.callbacks = append(mt.callbacks, AnsweredCallback{
		CallbackQueryID: formValue(r, "callback_query_id"),
		Text:            formValue(r, "text"),
		ShowAlert:       formValue(r, "show_alert") == "true",
	})
	mt.mu.Unlock()

	respondJSON(w, true)
}

func respondJSON(w http.ResponseWriter, result any) {
	resp := map[string]any{
		"ok":     true,
		"result": result,
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(resp)
}
