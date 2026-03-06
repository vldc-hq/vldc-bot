package app

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"
	"time"

	"github.com/vldc-hq/vldc-bot/internal/ai"
	"github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/config"
	"github.com/vldc-hq/vldc-bot/internal/observability"
	"github.com/vldc-hq/vldc-bot/internal/speech"
	storesqlite "github.com/vldc-hq/vldc-bot/internal/store/sqlite"
	"github.com/vldc-hq/vldc-bot/internal/translate"
)

type App struct {
	bot             *bot.Runtime
	db              *sql.DB
	logger          *slog.Logger
	sentryShutdown  observability.SentryShutdown
	shutdownTimeout time.Duration
}

func New(cfg config.Config) (*App, error) {
	logger := observability.NewLogger(cfg.Debug)

	sentryShutdown, err := observability.InitSentry(cfg.SentryDSN)
	if err != nil {
		return nil, fmt.Errorf("init sentry: %w", err)
	}

	db, err := storesqlite.Open(cfg.SQLiteDBPath)
	if err != nil {
		return nil, fmt.Errorf("open sqlite store: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := storesqlite.BootstrapSchema(ctx, db); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("bootstrap sqlite schema: %w", err)
	}

	var chatGen *ai.Fallback
	if cfg.GeminiAPIKey != "" || cfg.OpenAIAPIKey != "" {
		fallback, fallbackErr := ai.NewFallback(
			ai.NewGeminiStub(cfg.GeminiAPIKey),
			ai.NewOpenAIStub(cfg.OpenAIAPIKey),
		)
		if fallbackErr == nil {
			chatGen = fallback
		}
	}

	b, err := bot.New(cfg.Token, cfg.HTTPTimeout, logger, bot.Dependencies{
		Version:       "0.13.0-go",
		HTTPTimeout:   cfg.HTTPTimeout,
		AOCSession:    cfg.AOCSession,
		GroupChatID:   cfg.GroupChatID,
		TrustedUsers:  storesqlite.NewTrustedUsersRepo(db),
		SinceTopics:   storesqlite.NewSinceTopicsRepo(db),
		PrismWords:    storesqlite.NewPrismWordsRepo(db),
		Peninsula:     storesqlite.NewPeninsulaRepo(db),
		RollHussars:   storesqlite.NewRollHussarsRepo(db),
		AOC:           storesqlite.NewAOCRepo(db),
		Quarantine:    storesqlite.NewQuarantineRepo(db),
		Buktopuha:     storesqlite.NewBuktopuhaRepo(db),
		Modes:         bot.NewChatModes(),
		Roulette:      bot.NewRouletteState(),
		BuktopuhaGame: bot.NewBuktopuhaState(),
		BioChecker:    ai.NewHeuristicBioChecker(),
		ChatGenerator: chatGen,
		Speech:        speech.DisabledRecognizer{},
		Translator:    translate.DisabledTranslator{},
	})
	if err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("init telegram runtime: %w", err)
	}

	return &App{
		bot:             b,
		db:              db,
		logger:          logger,
		sentryShutdown:  sentryShutdown,
		shutdownTimeout: cfg.ShutdownTimeout,
	}, nil
}

func (a *App) Run(ctx context.Context) error {
	defer func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), a.shutdownTimeout)
		defer cancel()

		if a.db != nil {
			if err := a.db.Close(); err != nil {
				a.logger.Error("db close failed", "error", err)
			}
		}

		if err := a.sentryShutdown(shutdownCtx); err != nil {
			a.logger.Error("sentry flush failed", "error", err)
		}
	}()

	a.bot.Start(ctx)
	return nil
}
