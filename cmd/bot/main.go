package main

import (
	"context"
	"log"
	"log/slog"
	"os"
	"os/signal"
	"syscall"

	"github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/config"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/skill"
)

func main() {
	if err := run(); err != nil {
		log.Fatal(err)
	}
}

func run() error {
	cfg, err := config.Load()
	if err != nil {
		return err
	}

	if cfg.Debug {
		slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelDebug})))
	}

	database, err := db.New(cfg.SQLiteDBPath)
	if err != nil {
		return err
	}
	defer func() { _ = database.Close() }()

	skills := []bot.Skill{
		skill.CoreSkill(),
		skill.MuteSkill(),
		skill.BanSkill(),
		skill.BanmeSkill(),
		skill.RollSkill(),
		skill.TowelSkill(),
		skill.NyaSkill(),
		skill.SinceSkill(),
		skill.CocSkill(),
		skill.PrSkill(),
		skill.StillSkill(),
		skill.AtLeast70kSkill(),
		skill.TreeSkill(),
		skill.SmileModeSkill(),
		skill.TrustedSkill(),
		skill.PrismSkill(),
		skill.KozulaSkill(),
		skill.UwuSkill(),
		skill.LengthSkill(),
		skill.AocSkill(),
		skill.BuktopuhaSkill(),
		skill.ChatSkill(),
		skill.FoolsSkill(),
		skill.NastyaSkill(),
		skill.ModeCommandsSkill([]string{"towel_mode", "since_mode", "smile_mode", "fools_mode", "chat_mode", "nastya_mode"}),
	}

	b, err := bot.New(cfg, database, skills)
	if err != nil {
		return err
	}

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	return b.Run(ctx)
}
