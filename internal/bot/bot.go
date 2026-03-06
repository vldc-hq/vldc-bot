package bot

import (
	"context"
	"fmt"
	"log/slog"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	"github.com/vldc-hq/vldc-bot/internal/config"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/mode"
)

type Bot struct {
	cfg       *config.Config
	db        *db.DB
	tg        *bot.Bot
	modeState *mode.State
	skills    []Skill
}

// Skill defines a pluggable bot feature.
type Skill struct {
	Name string
	Hint string
	// Register is called during bot setup to register handlers.
	Register func(b *bot.Bot, deps *Deps)
}

// Deps holds shared dependencies injected into skills.
type Deps struct {
	DB        *db.DB
	Config    *config.Config
	ModeState *mode.State
}

func New(cfg *config.Config, database *db.DB, skills []Skill) (*Bot, error) {
	b := &Bot{
		cfg:       cfg,
		db:        database,
		modeState: mode.NewState(),
		skills:    skills,
	}
	return b, nil
}

func (b *Bot) Run(ctx context.Context) error {
	deps := &Deps{
		DB:        b.db,
		Config:    b.cfg,
		ModeState: b.modeState,
	}

	opts := []bot.Option{
		bot.WithDefaultHandler(func(ctx context.Context, tg *bot.Bot, update *models.Update) {}),
	}

	// Add chat filter middleware if CHAT_ID is set
	if b.cfg.GroupChatID != "" {
		opts = append(opts, bot.WithMiddlewares(chatFilterMiddleware(b.cfg)))
	}

	tg, err := bot.New(b.cfg.Token, opts...)
	if err != nil {
		return fmt.Errorf("create bot: %w", err)
	}
	b.tg = tg

	// Register all skills
	for _, skill := range b.skills {
		slog.Info("registering skill", "name", skill.Name)
		skill.Register(tg, deps)
	}

	// Set bot commands
	cmds := b.buildCommandList()
	if len(cmds) > 0 {
		_, err := tg.SetMyCommands(ctx, &bot.SetMyCommandsParams{
			Commands: cmds,
		})
		if err != nil {
			slog.Warn("failed to set bot commands", "error", err)
		}
	}

	slog.Info("starting bot polling")
	tg.Start(ctx)
	return nil
}

func (b *Bot) buildCommandList() []models.BotCommand {
	commands := []models.BotCommand{
		{Command: "nya", Description: "Simon says wat?"},
		{Command: "mute", Description: "mute user for N minutes"},
		{Command: "unmute", Description: "unmute user"},
		{Command: "hussars", Description: "show hussars leaderboard"},
		{Command: "wipe_hussars", Description: "wipe all hussars history"},
		{Command: "trust", Description: "in god we trust"},
		{Command: "untrust", Description: "how dare you?!"},
		{Command: "pr", Description: "got sk1lzz?"},
		{Command: "70k", Description: "try to hire!"},
		{Command: "coc", Description: "VLDC/GDG VL Code of Conduct"},
		{Command: "ban", Description: "ban! ban! ban!"},
		{Command: "roll", Description: "life is so cruel... isn't it?"},
		{Command: "since", Description: "when was the last time we discussed this?"},
		{Command: "since_list", Description: "hot topics"},
		{Command: "still", Description: "do u remember it?"},
		{Command: "top", Description: "top PRISM words"},
		{Command: "version", Description: "show bot version"},
		{Command: "gdpr_me", Description: "wipe all my hussar history"},
		{Command: "length", Description: "length of your instrument"},
		{Command: "longest", Description: "size doesn't matter, or is it?"},
		{Command: "banme", Description: "commit sudoku"},
		{Command: "tree", Description: "Advent of Code"},
		{Command: "kozula", Description: "exchange rate"},
		{Command: "znatoki", Description: "buktopuha leaderboard"},
	}
	return commands
}
