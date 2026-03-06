package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	Token           string
	Debug           bool
	SentryDSN       string
	SQLiteDBPath    string
	GroupChatID     string
	AOCSession      string
	OpenAIAPIKey    string
	GeminiAPIKey    string
	HTTPTimeout     time.Duration
	ShutdownTimeout time.Duration
}

func Load() (Config, error) {
	token := os.Getenv("TOKEN")
	if token == "" {
		return Config{}, fmt.Errorf("TOKEN is required")
	}

	debug, err := parseBoolEnv("DEBUG", false)
	if err != nil {
		return Config{}, err
	}

	httpTimeout, err := parseDurationEnv("HTTP_TIMEOUT", 30*time.Second)
	if err != nil {
		return Config{}, err
	}

	shutdownTimeout, err := parseDurationEnv("SHUTDOWN_TIMEOUT", 10*time.Second)
	if err != nil {
		return Config{}, err
	}

	return Config{
		Token:           token,
		Debug:           debug,
		SentryDSN:       os.Getenv("SENTRY_DSN"),
		SQLiteDBPath:    envOrDefault("SQLITE_DB_PATH", "bot.db"),
		GroupChatID:     os.Getenv("CHAT_ID"),
		AOCSession:      os.Getenv("AOC_SESSION"),
		OpenAIAPIKey:    os.Getenv("OPENAI_API_KEY"),
		GeminiAPIKey:    os.Getenv("GEMINI_API_KEY"),
		HTTPTimeout:     httpTimeout,
		ShutdownTimeout: shutdownTimeout,
	}, nil
}

func envOrDefault(name string, fallback string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}

	return fallback
}

func parseBoolEnv(name string, fallback bool) (bool, error) {
	raw := os.Getenv(name)
	if raw == "" {
		return fallback, nil
	}

	v, err := strconv.ParseBool(raw)
	if err != nil {
		return false, fmt.Errorf("invalid %s value %q: %w", name, raw, err)
	}

	return v, nil
}

func parseDurationEnv(name string, fallback time.Duration) (time.Duration, error) {
	raw := os.Getenv(name)
	if raw == "" {
		return fallback, nil
	}

	v, err := time.ParseDuration(raw)
	if err != nil {
		return 0, fmt.Errorf("invalid %s value %q: %w", name, raw, err)
	}

	return v, nil
}
