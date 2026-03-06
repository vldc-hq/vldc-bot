package skill

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"math/rand/v2"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	"github.com/vldc-hq/vldc-bot/internal/ai"
	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

const gameTimeSec = 30

var buktopuhaRegex = regexp.MustCompile(`(?i)/[вb][иu][kк][tт][оo][pр][иu][hн][aа]`)

var defaultWordlist = []string{
	"babirusa", "gerenuk", "pangolin", "capybara", "platypus",
	"armadillo", "axolotl", "wombat", "narwhal", "okapi",
	"quokka", "tapir", "dugong", "binturong", "fossa",
}

var yesWords = []string{
	"yes", "correct", "indeed", "yup", "yep", "yeah",
	"aha", "definitely", "affirmative", "right", "✅", "👍", "👏",
}

type buktopuhaGame struct {
	mu         sync.Mutex
	word       string
	startedAt  time.Time
	lastGameAt time.Time
	hintCancel context.CancelFunc
}

func newBuktopuhaGame() *buktopuhaGame {
	return &buktopuhaGame{}
}

func (g *buktopuhaGame) getWord() string {
	g.mu.Lock()
	defer g.mu.Unlock()
	return g.word
}

func (g *buktopuhaGame) canStart() bool {
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.word == "" && g.lastGameAt.IsZero() {
		return true
	}
	return g.word == "" && time.Since(g.lastGameAt) > gameTimeSec*time.Second
}

func (g *buktopuhaGame) sinceLastGame() time.Duration {
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.lastGameAt.IsZero() {
		return 24 * time.Hour
	}
	return time.Since(g.lastGameAt)
}

func (g *buktopuhaGame) start(word string, cancel context.CancelFunc) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.word = word
	g.startedAt = time.Now()
	g.lastGameAt = g.startedAt
	g.hintCancel = cancel
}

func (g *buktopuhaGame) stop() {
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.hintCancel != nil {
		g.hintCancel()
		g.hintCancel = nil
	}
	g.word = ""
}

func (g *buktopuhaGame) checkAnswer(text string) bool {
	g.mu.Lock()
	defer g.mu.Unlock()
	if g.word == "" {
		return false
	}
	return strings.Contains(strings.ToLower(text), g.word)
}

func (g *buktopuhaGame) score() int {
	g.mu.Lock()
	defer g.mu.Unlock()
	elapsed := time.Since(g.startedAt)
	remaining := gameTimeSec - int(elapsed.Seconds())
	if remaining < 0 {
		remaining = 0
	}
	return remaining + len(g.word)
}

func BuktopuhaSkill() appbot.Skill {
	game := newBuktopuhaGame()
	var database *db.DB
	var geminiKey, openaiKey string

	return appbot.Skill{
		Name: "buktopuha",
		Hint: "word guessing game",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			database = deps.DB
			geminiKey = deps.Config.GeminiAPIKey
			openaiKey = deps.Config.OpenAIAPIKey

			b.RegisterHandler(bot.HandlerTypeMessageText, "/znatoki", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleZnatoki(ctx, b, update, database)
			})

			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil || update.Message.Text == "" {
					return false
				}
				return buktopuhaRegex.MatchString(update.Message.Text)
			}, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleStartBuktopuha(ctx, b, update, game, database, geminiKey, openaiKey)
			})

			b.RegisterHandlerMatchFunc(func(update *models.Update) bool {
				if update.Message == nil || update.Message.Text == "" {
					return false
				}
				return game.checkAnswer(update.Message.Text)
			}, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleBuktopuhaAnswer(ctx, b, update, game, database)
			})
		},
	}
}

func handleStartBuktopuha(ctx context.Context, b *bot.Bot, update *models.Update, game *buktopuhaGame, database *db.DB, geminiKey, openaiKey string) {
	if update.Message == nil || update.Message.From == nil {
		return
	}
	msg := update.Message
	user := msg.From

	if !game.canStart() {
		result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: msg.Chat.ID,
			Text:   "Hey, not so fast!",
		})
		util.ScheduleCleanup(b, msg.Chat.ID, 10*time.Second, msg.ID, msgID(result))
		MuteUserForDuration(ctx, b, msg.Chat.ID, user.ID, user.FirstName, time.Minute)
		return
	}

	word := defaultWordlist[rand.IntN(len(defaultWordlist))]

	question := generateBuktopuhaQuestion(ctx, word, geminiKey, openaiKey)

	var text string
	if game.sinceLastGame() > 2*time.Hour {
		text = fmt.Sprintf("🎠 Starting the BukToPuHa! 🎪\nTry to guess the word in %d seconds:\n\n%s", gameTimeSec, question)
	} else {
		text = question
	}

	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: msg.Chat.ID,
		Text:   text,
	})

	hintCtx, cancel := context.WithCancel(context.Background())
	game.start(word, cancel)

	// Schedule hints and end in background
	chatID := msg.Chat.ID
	go runBuktopuhaTimers(hintCtx, b, chatID, game, word)

	// Track game participation
	meta, _ := json.Marshal(map[string]string{
		"username":   user.Username,
		"first_name": user.FirstName,
		"last_name":  user.LastName,
	})
	existing, _ := database.FindBuktopuhaPlayer(user.ID)
	if existing == nil {
		_ = database.AddBuktopuhaPlayer(user.ID, string(meta), 0)
	} else {
		_ = database.IncBuktopuhaGameCounter(user.ID)
	}
}

func runBuktopuhaTimers(ctx context.Context, b *bot.Bot, chatID int64, game *buktopuhaGame, word string) {
	// Hint 1 at 10s
	select {
	case <-ctx.Done():
		return
	case <-time.After(10 * time.Second):
	}

	if game.getWord() != word {
		return
	}
	charIdx := rand.IntN(len(word))
	char := word[charIdx]
	masked := make([]byte, len(word))
	for i := range word {
		if word[i] == char {
			masked[i] = char
		} else {
			masked[i] = '*'
		}
	}
	hint1, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text:   fmt.Sprintf("First hint: %s", string(masked)),
	})
	util.ScheduleCleanup(b, chatID, 30*time.Second, msgID(hint1))

	// Hint 2 at 20s
	select {
	case <-ctx.Done():
		return
	case <-time.After(10 * time.Second):
	}

	if game.getWord() != word {
		return
	}
	letters := []byte(word)
	rand.Shuffle(len(letters), func(i, j int) { letters[i], letters[j] = letters[j], letters[i] })
	hint2, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text:   fmt.Sprintf("Second hint (anagram): %s", string(letters)),
	})
	util.ScheduleCleanup(b, chatID, 30*time.Second, msgID(hint2))

	// End at 30s
	select {
	case <-ctx.Done():
		return
	case <-time.After(10 * time.Second):
	}

	if game.getWord() != word {
		return
	}
	game.stop()
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: chatID,
		Text:   fmt.Sprintf("Nobody guessed the word %s 😢", word),
	})
}

func handleBuktopuhaAnswer(ctx context.Context, b *bot.Bot, update *models.Update, game *buktopuhaGame, database *db.DB) {
	if update.Message == nil || update.Message.From == nil {
		return
	}
	msg := update.Message
	user := msg.From

	word := game.getWord()
	if word == "" {
		return
	}

	if !strings.Contains(strings.ToLower(msg.Text), word) {
		return
	}

	score := game.score()
	game.stop()

	yes := yesWords[rand.IntN(len(yesWords))]
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:          msg.Chat.ID,
		Text:            yes,
		ReplyParameters: &models.ReplyParameters{MessageID: msg.ID},
	})

	// Felix Felicis — 10% chance of random ban
	if rand.Float64() < 0.1 {
		minutes := rand.IntN(10) + 1
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID:          msg.Chat.ID,
			Text:            fmt.Sprintf("Oh, you're lucky! You get a prize: ban for %d min!", minutes),
			ReplyParameters: &models.ReplyParameters{MessageID: msg.ID},
		})
		MuteUserForDuration(ctx, b, msg.Chat.ID, user.ID, user.FirstName, time.Duration(minutes)*time.Minute)
	}

	// Update score
	meta, _ := json.Marshal(map[string]string{
		"username":   user.Username,
		"first_name": user.FirstName,
		"last_name":  user.LastName,
	})
	existing, _ := database.FindBuktopuhaPlayer(user.ID)
	if existing == nil {
		_ = database.AddBuktopuhaPlayer(user.ID, string(meta), score)
	} else {
		_ = database.IncBuktopuhaWin(user.ID, score)
	}
}

func handleZnatoki(ctx context.Context, b *bot.Bot, update *models.Update, database *db.DB) {
	if update.Message == nil {
		return
	}

	players, err := database.GetAllBuktopuhaPlayers()
	if err != nil || len(players) == 0 {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: update.Message.Chat.ID,
			Text:   "No players yet 🤷",
		})
		return
	}

	board := fmt.Sprintf("%-12s | %-9s | %-9s | %s\n", "score", "games", "wins", "znatok")
	board += "------------ + --------- + --------- + ----------------\n"
	for _, p := range players {
		board += fmt.Sprintf("%-12d | %-9d | %-9d | %s\n",
			p.TotalScore, p.GameCounter, p.WinCounter, p.Username())
	}

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID:    update.Message.Chat.ID,
		Text:      fmt.Sprintf("```\n%s```", board),
		ParseMode: models.ParseModeMarkdown,
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 600*time.Second, update.Message.ID, msgID(result))
}

func generateBuktopuhaQuestion(ctx context.Context, word, geminiKey, openaiKey string) string {
	prompt := fmt.Sprintf(`You are a facilitator of an online quiz game.
Your task is to make engaging and tricky quiz questions.
You should try to make your question fun and interesting, but keep your wording simple and short (less than 15 words).
Keep in mind that for part of the audience English is not a native language.
You can use historical references or examples to explain the word.

Please write a quiz question for the word '%s' using single sentence without mentioning the word itself.`, word)

	fallback := fmt.Sprintf("Guess the word. It has %d letters.", len(word))

	// Try Gemini first if available
	if geminiKey != "" {
		geminiModels := []string{"gemini-2.5-flash", "gemini-2.0-flash"}
		model := geminiModels[rand.IntN(len(geminiModels))]
		text, err := ai.GeminiGenerate(ctx, geminiKey, model, "", []string{prompt})
		if err == nil {
			cleaned := strings.TrimSpace(strings.Trim(text, "\""))
			// Censor the word from the response
			cleaned = censorWord(cleaned, word)
			return fmt.Sprintf("%s: %s", model, cleaned)
		}
		slog.Warn("gemini question failed", "error", err)
	}

	// Try OpenAI
	if openaiKey != "" {
		openaiModels := []string{"gpt-4o-mini"}
		model := openaiModels[rand.IntN(len(openaiModels))]
		text, err := ai.OpenAIGenerate(ctx, openaiKey, model, prompt)
		if err == nil {
			cleaned := strings.TrimSpace(strings.Trim(text, "\""))
			cleaned = censorWord(cleaned, word)
			return fmt.Sprintf("%s: %s", model, cleaned)
		}
		slog.Warn("openai question failed", "error", err)
	}

	return fallback
}

func censorWord(text, word string) string {
	re := regexp.MustCompile("(?i)" + regexp.QuoteMeta(word))
	return re.ReplaceAllString(text, "***")
}
