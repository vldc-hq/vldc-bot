package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

type Config struct {
	Token           string
	Debug           bool
	GroupChatID     string
	SQLiteDBPath    string
	SentryDSN       string
	AOCSession      string
	GoogleProjectID string
	GeminiAPIKey    string
	OpenAIAPIKey    string
}

func Load() (*Config, error) {
	token := os.Getenv("TOKEN")
	if token == "" {
		return nil, fmt.Errorf("TOKEN env variable is required")
	}

	debug, _ := strconv.ParseBool(os.Getenv("DEBUG"))

	dbPath := os.Getenv("SQLITE_DB_PATH")
	if dbPath == "" {
		dbPath = "bot.db"
	}

	chatID := strings.TrimSpace(os.Getenv("CHAT_ID"))

	return &Config{
		Token:           token,
		Debug:           debug,
		GroupChatID:     chatID,
		SQLiteDBPath:    dbPath,
		SentryDSN:       os.Getenv("SENTRY_DSN"),
		AOCSession:      os.Getenv("AOC_SESSION"),
		GoogleProjectID: os.Getenv("GOOGLE_PROJECT_ID"),
		GeminiAPIKey:    os.Getenv("GEMINI_API_KEY"),
		OpenAIAPIKey:    os.Getenv("OPENAI_API_KEY"),
	}, nil
}

// ChatID returns the group chat ID as int64 if possible, 0 otherwise.
func (c *Config) ChatID() int64 {
	if c.GroupChatID == "" {
		return 0
	}
	id, err := strconv.ParseInt(c.GroupChatID, 10, 64)
	if err != nil {
		return 0
	}
	return id
}
