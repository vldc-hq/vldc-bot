package skill

import (
	"context"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"regexp"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	"github.com/vldc-hq/vldc-bot/internal/ai"
	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

const (
	chatModeName  = "chat_mode"
	maxMessages   = 100
	maxAge        = 12 * time.Hour
	sleepInterval = time.Hour
	poemsPerDay   = 2
	maxTries      = 10
	minMessages   = 5
	geminiModel   = "gemini-2.5-flash"
)

var vowelPattern = regexp.MustCompile(`[аеёиоуыэюяАЕЁИОУЫЭЮЯ]`)

type chatMessage struct {
	timestamp time.Time
	text      string
}

type nyanBot struct {
	mu     sync.Mutex
	memory []chatMessage
}

func newNyanBot() *nyanBot {
	return &nyanBot{
		memory: make([]chatMessage, 0, maxMessages),
	}
}

func (n *nyanBot) addMessage(fullName, text string) {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.memory = append(n.memory, chatMessage{
		timestamp: time.Now(),
		text:      fmt.Sprintf("%s: %s", fullName, text),
	})
	if len(n.memory) > maxMessages {
		n.memory = n.memory[len(n.memory)-maxMessages:]
	}
}

func (n *nyanBot) getRecentMessages() []string {
	n.mu.Lock()
	defer n.mu.Unlock()
	cutoff := time.Now().Add(-maxAge)
	result := make([]string, 0, len(n.memory))
	for _, m := range n.memory {
		if m.timestamp.After(cutoff) {
			result = append(result, m.text)
		}
	}
	return result
}

func (n *nyanBot) forget() {
	n.mu.Lock()
	defer n.mu.Unlock()
	n.memory = n.memory[:0]
}

func ChatSkill() appbot.Skill {
	nyan := newNyanBot()

	return appbot.Skill{
		Name: "chat_mode",
		Hint: "poem generator (pirozhki)",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			if deps.Config.GeminiAPIKey == "" {
				slog.Info("chat_mode: GEMINI_API_KEY not set, skipping")
				return
			}

			deps.ModeState.Register(&mode.ModeConfig{
				Name:      chatModeName,
				DefaultOn: true,
				OffCallback: func() {
					nyan.forget()
				},
			})

			// Listen to all text messages
			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil || update.Message.Text == "" {
					return false
				}
				if strings.HasPrefix(update.Message.Text, "/") {
					return false
				}
				return deps.ModeState.IsEnabled(update.Message.Chat.ID, chatModeName)
			}, func(_ context.Context, _ *bot.Bot, update *models.Update) {
				if update.Message.From == nil {
					return
				}
				fullName := update.Message.From.FirstName
				if update.Message.From.LastName != "" {
					fullName += " " + update.Message.From.LastName
				}
				nyan.addMessage(fullName, update.Message.Text)
			})

			// Start muse goroutine
			chatID := deps.Config.ChatID()
			if chatID != 0 {
				go runMuse(b, deps, nyan, chatID)
			}
		},
	}
}

func runMuse(b *bot.Bot, deps *appbot.Deps, nyan *nyanBot, chatID int64) {
	ticker := time.NewTicker(sleepInterval)
	defer ticker.Stop()

	for range ticker.C {
		if !deps.ModeState.IsEnabled(chatID, chatModeName) {
			continue
		}

		// Random chance: poemsPerDay times per day
		secondsInDay := float64(24 * 60 * 60)
		inspirationRate := float64(poemsPerDay) / (secondsInDay / sleepInterval.Seconds())
		if rand.Float64() > inspirationRate {
			continue
		}

		poem := writePoem(deps.Config.GeminiAPIKey, nyan)
		if poem == "" {
			continue
		}

		ctx := context.Background()
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: chatID,
			Text:   poem,
		})
		nyan.forget()
	}
}

func writePoem(apiKey string, nyan *nyanBot) string {
	messages := nyan.getRecentMessages()
	if len(messages) < minMessages {
		slog.Info("not writing poem, too few messages", "count", len(messages))
		return ""
	}

	systemPrompt := `Ты чат бот владивостокского коммьюнити разработчиков VLDC.
Ты написан на Go но в тайне хотел бы переписать себя на Rust.
Тебя зовут Нян и твой аватар это пиксельный оранжевый кот с тигриными полосками.
Ты мастер коротких забавных (часто саркастических) стихов в стиле пирожок.
Этот стиль использует метрику ямбического тетраметра с количеством слогов 9-8-9-8 без рифмы, знаков препинания или заглавных букв.
Пирожок всегда состоит из 4 строк.`

	// Summarize the chat log for theme
	chatLog := strings.Join(messages, "\n")
	theme := summarizeChat(apiKey, chatLog)

	userMessages := []string{
		fmt.Sprintf(`Пожалуйста, напиши лучший пирожок! Ровно 4 строки, не больше не меньше.
Этот пирожок должен стать легендой, он должен быть максимально гениальным и смешным.
Тема пирожка:
%s.`, theme),
	}

	for range maxTries {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		text, err := ai.GeminiGenerate(ctx, apiKey, geminiModel, systemPrompt, userMessages)
		cancel()

		if err != nil {
			slog.Warn("poem generation failed", "error", err)
			continue
		}

		errMsg := checkPirozhok(text)
		if errMsg == "" {
			return text
		}

		userMessages = append(userMessages, fmt.Sprintf("%s\nПопробуй ещё раз.", errMsg))
	}

	return ""
}

func summarizeChat(apiKey, chatLog string) string {
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	systemPrompt := "Ты языковая модель, специализирующаяся на суммаризации текста. Ты всегда выдаёшь чёткую выжимку в одном предложении на русском языке без форматирования."
	text, err := ai.GeminiGenerate(ctx, apiKey, geminiModel, systemPrompt, []string{
		"Дай выжимку из следующего текста на русском языке в одном предложении, без форматирования.\n" + chatLog,
	})
	if err != nil {
		slog.Warn("summary failed", "error", err)
		if len(chatLog) > 200 {
			return chatLog[:200]
		}
		return chatLog
	}
	return text
}

func checkPirozhok(pirozhok string) string {
	syllableCounts := [4]int{9, 8, 9, 8}
	nonCyrillic := regexp.MustCompile(`[^абвгдеёжзийклмнопрстуфхцчшщъыьэюя\s]`)

	for _, word := range strings.Fields(pirozhok) {
		if nonCyrillic.MatchString(strings.ToLower(word)) {
			return fmt.Sprintf("Слово %s содержит не кириллические символы.", word)
		}
	}

	lines := strings.Split(strings.TrimSpace(pirozhok), "\n")
	if len(lines) != 4 {
		return "Пирожок должен состоять из 4 строк."
	}

	for i, line := range lines {
		cnt := utf8.RuneCountInString(strings.Join(vowelPattern.FindAllString(line, -1), ""))
		if cnt != syllableCounts[i] {
			return fmt.Sprintf("В строке %d (%s) должно быть %d слогов, а не %d.", i+1, line, syllableCounts[i], cnt)
		}
	}

	return ""
}
