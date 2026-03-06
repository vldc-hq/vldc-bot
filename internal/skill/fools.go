package skill

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"cloud.google.com/go/translate"
	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
	"golang.org/x/text/language"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

const foolsModeName = "fools_mode"

var foolsLanguages = []string{"ro", "uk", "sr", "sk", "sl", "uz", "bg", "mn", "kk"}

func FoolsSkill() appbot.Skill {
	return appbot.Skill{
		Name: "fools_mode",
		Hint: "translation mode",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			deps.ModeState.Register(&mode.ModeConfig{
				Name:      foolsModeName,
				DefaultOn: false,
			})

			var tc *translate.Client
			if deps.Config.GoogleProjectID != "" {
				var err error
				tc, err = translate.NewClient(context.Background())
				if err != nil {
					slog.Error("fools_mode: failed to create translate client", "error", err)
				}
			}

			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil || update.Message.Text == "" {
					return false
				}
				if strings.HasPrefix(update.Message.Text, "/") {
					return false
				}
				return deps.ModeState.IsEnabled(update.Message.Chat.ID, foolsModeName)
			}, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleFoolsMode(ctx, b, update, tc, deps.Config.GeminiAPIKey)
			})
		},
	}
}

func handleFoolsMode(ctx context.Context, b *bot.Bot, update *models.Update, tc *translate.Client, geminiKey string) {
	if update.Message == nil || update.Message.From == nil {
		return
	}
	msg := update.Message
	user := msg.From

	fullName := user.FirstName
	if user.LastName != "" {
		fullName += " " + user.LastName
	}

	// Deterministic language based on user's full name
	magicNumber := 0
	for _, c := range fullName {
		magicNumber += int(c)
	}
	lang := foolsLanguages[magicNumber%len(foolsLanguages)]
	emoji := string(rune(0x1F600 + magicNumber%75))

	// Special case
	if user.Username == "KittyHawk1" {
		lang = "he"
		emoji = "\U0001F9D8\u200D\u2642\uFE0F"
	}

	_, _ = b.DeleteMessage(ctx, &bot.DeleteMessageParams{ChatID: msg.Chat.ID, MessageID: msg.ID})

	translated := translateText(ctx, msg.Text, lang, tc, geminiKey)

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   fmt.Sprintf("%s %s: %s", emoji, fullName, translated),
	})
}

// translateText uses Google Cloud Translate API (primary) or Gemini (fallback).
func translateText(ctx context.Context, text, targetLang string, tc *translate.Client, geminiKey string) string {
	if tc != nil {
		tag, err := language.Parse(targetLang)
		if err == nil {
			translations, err := tc.Translate(ctx, []string{text}, tag, &translate.Options{
				Source: language.Russian,
				Format: translate.Text,
			})
			if err == nil && len(translations) > 0 && translations[0].Text != "" {
				return translations[0].Text
			}
			slog.Debug("cloud translate failed", "error", err)
		} else {
			slog.Debug("failed to parse target language", "lang", targetLang, "error", err)
		}
	}

	// Fallback to Gemini if available
	if geminiKey != "" {
		return geminiTranslate(ctx, text, targetLang, geminiKey)
	}

	return text
}

func geminiTranslate(ctx context.Context, text, targetLang, apiKey string) string {
	prompt := fmt.Sprintf("Translate the following text from Russian to %s. Return only the translation, nothing else.\n\n%s", targetLang, text)

	ctx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()

	translated, err := geminiSimpleCall(ctx, apiKey, prompt)
	if err != nil {
		slog.Warn("gemini translate failed", "error", err)
		return text
	}
	return translated
}

func geminiSimpleCall(ctx context.Context, apiKey, prompt string) (string, error) {
	reqBody := map[string]any{
		"contents": []map[string]any{
			{"parts": []map[string]string{{"text": prompt}}},
		},
	}
	bodyBytes, _ := json.Marshal(reqBody)

	apiURL := fmt.Sprintf("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=%s", apiKey)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, apiURL, strings.NewReader(string(bodyBytes)))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 15 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	var result struct {
		Candidates []struct {
			Content struct {
				Parts []struct {
					Text string `json:"text"`
				} `json:"parts"`
			} `json:"content"`
		} `json:"candidates"`
	}
	if err := json.Unmarshal(respBody, &result); err != nil {
		return "", err
	}

	if len(result.Candidates) > 0 && len(result.Candidates[0].Content.Parts) > 0 {
		return result.Candidates[0].Content.Parts[0].Text, nil
	}

	return "", fmt.Errorf("empty gemini response")
}
