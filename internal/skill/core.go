package skill

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

const Version = "1.0.0"

func CoreSkill() appbot.Skill {
	return appbot.Skill{
		Name: "core",
		Hint: "core commands",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/start", bot.MatchTypePrefix, handleStart)
			b.RegisterHandler(bot.HandlerTypeMessageText, "/help", bot.MatchTypePrefix, handleHelp)
			b.RegisterHandler(bot.HandlerTypeMessageText, "/version", bot.MatchTypePrefix, handleVersion)
		},
	}
}

func handleStart(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   "I'm a VLDC Bot.\n\nMy source: https://github.com/vldc-hq/vldc-bot",
	})
}

func handleHelp(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text: "The bot should be an admin with all admins permissions\n\n" +
			"Skills for admins:\n" +
			"/mute [duration] — mute user (reply)\n" +
			"/unmute — unmute user (reply)\n" +
			"/ban — ban user (reply)\n" +
			"/trust — trust user (reply)\n" +
			"/untrust — untrust user (reply)\n" +
			"/wipe_hussars — clear hussar data\n\n" +
			"Skills for all:\n" +
			"/roll — Russian roulette\n" +
			"/banme — commit sudoku\n" +
			"/hussars — leaderboard\n" +
			"/gdpr_me — wipe your hussar data\n" +
			"/since [topic] — topic tracker\n" +
			"/since_list — hot topics\n" +
			"/nya — meow\n" +
			"/still [text] — nostalgia\n" +
			"/70k — hiring advice\n" +
			"/tree — Advent of Code\n" +
			"/kozula — exchange rate\n" +
			"/top — top words\n" +
			"/length — measure your ID\n" +
			"/longest — top measurements\n" +
			"/znatoki — buktopuha leaderboard\n" +
			"/coc — Code of Conduct\n" +
			"/pr — got skillz?\n\n" +
			"Modes: towel_mode, since_mode, smile_mode, fools_mode, chat_mode, nastya_mode\n" +
			"Toggle: /<mode>_on, /<mode>_off, /<mode>\n\n" +
			"https://github.com/vldc-hq/vldc-bot/issues",
	})
}

func handleVersion(ctx context.Context, b *bot.Bot, update *models.Update) {
	if update.Message == nil {
		return
	}
	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   fmt.Sprintf("~=~~=~=~=_ver.:%s_~=~=~=[,,_,,]:3", Version),
	})
	util.ScheduleCleanup(b, update.Message.Chat.ID, 120*time.Second, update.Message.ID, msgID(result))
}

func FormatSkillList(skills []appbot.Skill) string {
	var sb strings.Builder
	for _, s := range skills {
		fmt.Fprintf(&sb, "%s — %s\n", s.Name, s.Hint)
	}
	return sb.String()
}
