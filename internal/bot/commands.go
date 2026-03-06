package bot

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"
)

func buildCommandSpecs(deps Dependencies) []CommandSpec {
	return []CommandSpec{
		{Name: "start", Description: "Start bot", Handler: handleStart},
		{Name: "help", Description: "Show help", Handler: handleHelp},
		{Name: "version", Description: "Show version", Handler: handleVersion(deps), RequireAdmin: true},
		{Name: "trust", Handler: handleTrust(deps), RequireAdmin: true},
		{Name: "untrust", Handler: handleUntrust(deps), RequireAdmin: true},
		{Name: "since", Handler: handleSince(deps)},
		{Name: "since_list", Handler: handleSinceList(deps)},
		{Name: "prism", Handler: handlePrism(deps), RequireAdmin: true},
		{Name: "ban", Description: "Ban replied user", Handler: handleBan, RequireAdmin: true},
		{Name: "mute", Description: "Mute replied user", Handler: handleMute, RequireAdmin: true},
		{Name: "unmute", Description: "Unmute replied user", Handler: handleUnmute, RequireAdmin: true},
		{Name: "length", Handler: handleLength(deps)},
		{Name: "longest", Handler: handleLongest(deps)},
		{Name: "roll", Handler: handleRoll(deps)},
		{Name: "hussars", Handler: handleHussars(deps)},
		{Name: "wipe_hussars", Handler: handleWipeHussars(deps), RequireAdmin: true},
		{Name: "gdpr_me", Handler: handleGDPRMe(deps)},
		{Name: "smile_mode_on", Handler: handleSmileModeOn(deps), RequireAdmin: true},
		{Name: "smile_mode_off", Handler: handleSmileModeOff(deps), RequireAdmin: true},
		{Name: "smile_mode", Handler: handleSmileModeStatus(deps)},
		{Name: "towel_mode_on", Handler: handleTowelModeOn(deps), RequireAdmin: true},
		{Name: "towel_mode_off", Handler: handleTowelModeOff(deps), RequireAdmin: true},
		{Name: "towel_mode", Handler: handleTowelModeStatus(deps)},
		{Name: "chat_mode_on", Handler: handleChatModeOn(deps), RequireAdmin: true},
		{Name: "chat_mode_off", Handler: handleChatModeOff(deps), RequireAdmin: true},
		{Name: "chat_mode", Handler: handleChatModeStatus(deps)},
		{Name: "chat_now", Description: "Send chat tick now", Handler: handleChatNow(deps), RequireAdmin: true},
		{Name: "fools_mode_on", Handler: handleFoolsModeOn(deps), RequireAdmin: true},
		{Name: "fools_mode_off", Handler: handleFoolsModeOff(deps), RequireAdmin: true},
		{Name: "fools_mode", Handler: handleFoolsModeStatus(deps)},
		{Name: "nastya_mode_on", Handler: handleNastyaModeOn(deps), RequireAdmin: true},
		{Name: "nastya_mode_off", Handler: handleNastyaModeOff(deps), RequireAdmin: true},
		{Name: "nastya_mode", Handler: handleNastyaModeStatus(deps)},
		{Name: "znatoki", Handler: handleZnatoki(deps)},
		{Name: "buktopuha", Handler: handleBuktopuha(deps)},
		{Name: "aoc_status", Handler: handleAOCStatus(deps), RequireAdmin: true},
		{Name: "aoc_refresh", Handler: handleAOCRefresh(deps), RequireAdmin: true},
	}
}

func handleStart(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
	return tg.SendMessage(ctx, in.ChatID, "I'm a VLDC Bot. :3\n\nMy source: https://github.com/vldc-hq/vldc-bot")
}

func handleHelp(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
	msg := strings.Join([]string{
		"Available commands:",
		"/start",
		"/help",
		"/version (admin)",
		"/trust (admin, reply)",
		"/untrust (admin, reply)",
		"/since TOPIC",
		"/since_list",
		"/prism (admin)",
		"/ban (admin, reply)",
		"/mute N (admin, reply)",
		"/unmute (admin, reply)",
		"/length",
		"/longest",
		"/roll",
		"/hussars",
		"/wipe_hussars (admin)",
		"/gdpr_me",
		"/smile_mode_on (admin)",
		"/smile_mode_off (admin)",
		"/smile_mode",
		"/towel_mode_on (admin)",
		"/towel_mode_off (admin)",
		"/towel_mode",
		"/chat_mode_on (admin)",
		"/chat_mode_off (admin)",
		"/chat_mode",
		"/chat_now (admin)",
		"/fools_mode_on (admin)",
		"/fools_mode_off (admin)",
		"/fools_mode",
		"/nastya_mode_on (admin)",
		"/nastya_mode_off (admin)",
		"/nastya_mode",
		"/znatoki",
		"/buktopuha",
		"/aoc_status (admin)",
		"/aoc_refresh (admin)",
	}, "\n")

	return tg.SendMessage(ctx, in.ChatID, msg)
}

func handleVersion(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		version := deps.Version
		if version == "" {
			version = "dev"
		}

		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("~=~~=~=~=_ver.:%s_=~=~=~=[,,_,,]:3", version))
	}
}

func handleTrust(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.TrustedUsers == nil {
			return tg.SendMessage(ctx, in.ChatID, "trusted storage is not configured")
		}
		if in.ReplyToID == 0 {
			return tg.SendMessage(ctx, in.ChatID, "use /trust as reply to a user message")
		}

		existing, ok, err := deps.TrustedUsers.Get(ctx, in.ReplyToID)
		if err != nil {
			return err
		}
		if ok {
			return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d is already trusted", existing.UserID))
		}

		if err := deps.TrustedUsers.Upsert(ctx, in.ReplyToID, in.UserID, time.Now()); err != nil {
			return err
		}

		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d is trusted now", in.ReplyToID))
	}
}

func handleUntrust(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.TrustedUsers == nil {
			return tg.SendMessage(ctx, in.ChatID, "trusted storage is not configured")
		}
		if in.ReplyToID == 0 {
			return tg.SendMessage(ctx, in.ChatID, "use /untrust as reply to a user message")
		}

		if err := deps.TrustedUsers.Delete(ctx, in.ReplyToID); err != nil {
			return err
		}

		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d lost confidence", in.ReplyToID))
	}
}

func handleSince(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.SinceTopics == nil {
			return tg.SendMessage(ctx, in.ChatID, "since storage is not configured")
		}

		topic := strings.TrimSpace(strings.Join(in.Args, " "))
		if topic == "" {
			return tg.SendMessage(ctx, in.ChatID, "topic is empty")
		}
		if len(topic) > 64 {
			return tg.SendMessage(ctx, in.ChatID, "topic too long")
		}

		row, ok, err := deps.SinceTopics.Get(ctx, topic)
		if err != nil {
			return err
		}
		if !ok {
			row.Topic = strings.ToLower(topic)
			row.SinceDateTime = time.Now()
			row.Count = 1
		}

		days := int(time.Since(row.SinceDateTime).Hours() / 24)
		msg := fmt.Sprintf("%d days without «%s»! Already was discussed %d times", days, row.Topic, row.Count)

		if err := tg.SendMessage(ctx, in.ChatID, msg); err != nil {
			return err
		}

		return deps.SinceTopics.Upsert(ctx, row.Topic, row.SinceDateTime, row.Count)
	}
}

func handleSinceList(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.SinceTopics == nil {
			return tg.SendMessage(ctx, in.ChatID, "since storage is not configured")
		}

		topics, err := deps.SinceTopics.ListTop(ctx, 20)
		if err != nil {
			return err
		}
		if len(topics) == 0 {
			return tg.SendMessage(ctx, in.ChatID, "nothing yet :(")
		}

		lines := make([]string, 0, len(topics))
		for _, topic := range topics {
			days := int(time.Since(topic.SinceDateTime).Hours() / 24)
			lines = append(lines, fmt.Sprintf("%d days without «%s»! Already was discussed %d times", days, topic.Topic, topic.Count))
		}

		return tg.SendMessage(ctx, in.ChatID, strings.Join(lines, "\n"))
	}
}

func handlePrism(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.PrismWords == nil {
			return tg.SendMessage(ctx, in.ChatID, "prism storage is not configured")
		}

		words, err := deps.PrismWords.ListAll(ctx)
		if err != nil {
			return err
		}
		if len(words) == 0 {
			return tg.SendMessage(ctx, in.ChatID, "no prism words yet")
		}

		limit := 10
		if len(in.Args) > 0 {
			if n, convErr := strconv.Atoi(in.Args[0]); convErr == nil && n > 0 && n <= 100 {
				limit = n
			}
		}

		if len(words) < limit {
			limit = len(words)
		}

		lines := make([]string, 0, limit)
		for _, w := range words[:limit] {
			lines = append(lines, fmt.Sprintf("%s: %d", w.Word, w.Count))
		}

		return tg.SendMessage(ctx, in.ChatID, strings.Join(lines, "\n"))
	}
}

func handleBan(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
	if in.ReplyToID == 0 {
		return tg.SendMessage(ctx, in.ChatID, "use /ban as reply to a user message")
	}

	if err := tg.BanChatMember(ctx, in.ChatID, in.ReplyToID); err != nil {
		return err
	}

	return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d was banned", in.ReplyToID))
}

func handleMute(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
	if in.ReplyToID == 0 {
		return tg.SendMessage(ctx, in.ChatID, "use /mute as reply to a user message")
	}

	minutes := 60
	if len(in.Args) > 0 {
		if parsed, err := strconv.Atoi(in.Args[0]); err == nil && parsed > 0 {
			minutes = parsed
		}
	}

	if err := tg.RestrictChatMember(ctx, in.ChatID, in.ReplyToID, minutes); err != nil {
		return err
	}

	return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d was muted for %d minutes", in.ReplyToID, minutes))
}

func handleUnmute(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
	if in.ReplyToID == 0 {
		return tg.SendMessage(ctx, in.ChatID, "use /unmute as reply to a user message")
	}

	if err := tg.UnbanChatMember(ctx, in.ChatID, in.ReplyToID); err != nil {
		return err
	}

	return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d was unmuted", in.ReplyToID))
}

func handleLength(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if in.UserID == 0 {
			return nil
		}

		if deps.Peninsula != nil {
			meta := fmt.Sprintf(`{"user_id":%d}`, in.UserID)
			if err := deps.Peninsula.Upsert(ctx, in.UserID, meta); err != nil {
				return err
			}
		}

		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("Your telegram id length is %d (%d)", len(strconv.FormatInt(in.UserID, 10)), in.UserID))
	}
}

func handleLongest(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Peninsula == nil {
			return tg.SendMessage(ctx, in.ChatID, "length storage is not configured")
		}

		users, err := deps.Peninsula.ListTop(ctx, 10)
		if err != nil {
			return err
		}
		if len(users) == 0 {
			return tg.SendMessage(ctx, in.ChatID, "no data yet")
		}

		lines := make([]string, 0, len(users)+1)
		lines = append(lines, "Top known lengths:")
		for i, u := range users {
			lines = append(lines, fmt.Sprintf("%d -> %d", i+1, u.UserID))
		}

		return tg.SendMessage(ctx, in.ChatID, strings.Join(lines, "\n"))
	}
}

func handleRoll(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if in.UserID == 0 {
			return nil
		}
		if deps.RollHussars == nil || deps.Roulette == nil {
			return tg.SendMessage(ctx, in.ChatID, "roll is not configured")
		}

		now := time.Now()
		if _, ok, err := deps.RollHussars.Get(ctx, in.UserID); err != nil {
			return err
		} else if !ok {
			meta := fmt.Sprintf(`{"user_id":%d,"username":%q,"first_name":%q,"last_name":%q}`, in.UserID, in.Username, in.FirstName, in.LastName)
			if err := deps.RollHussars.Add(ctx, in.UserID, meta, now); err != nil {
				return err
			}
		}

		isShot, shotsRemain := deps.Roulette.Shot(in.ChatID)
		if isShot {
			muteMinutes := 16 * 60 * (6 - shotsRemain)
			if err := tg.RestrictChatMember(ctx, in.ChatID, in.UserID, muteMinutes); err != nil {
				return err
			}
			if err := deps.RollHussars.MarkDead(ctx, in.UserID, muteMinutes, now); err != nil {
				return err
			}
			return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("boom! user %d is dead [%dh mute]", in.UserID, muteMinutes/60))
		}

		if err := deps.RollHussars.MarkMiss(ctx, in.UserID, now); err != nil {
			return err
		}

		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("user %d: MISS! shots remain: %d", in.UserID, shotsRemain))
	}
}

func handleHussars(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.RollHussars == nil {
			return tg.SendMessage(ctx, in.ChatID, "hussars storage is not configured")
		}

		hussars, err := deps.RollHussars.ListAll(ctx)
		if err != nil {
			return err
		}
		if len(hussars) == 0 {
			return tg.SendMessage(ctx, in.ChatID, "No hussars in da club")
		}

		lines := []string{"Hussars leaderboard:"}
		for i, h := range hussars {
			lines = append(lines, fmt.Sprintf("%d) user:%d shots:%d deaths:%d time:%s", i+1, h.UserID, h.ShotCounter, h.DeadCounter, time.Duration(h.TotalTimeInClub)*time.Second))
			if i >= 9 {
				break
			}
		}

		return tg.SendMessage(ctx, in.ChatID, strings.Join(lines, "\n"))
	}
}

func handleWipeHussars(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.RollHussars == nil {
			return tg.SendMessage(ctx, in.ChatID, "hussars storage is not configured")
		}
		if err := deps.RollHussars.DeleteAll(ctx); err != nil {
			return err
		}
		return tg.SendMessage(ctx, in.ChatID, "all hussars history wiped")
	}
}

func handleGDPRMe(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if in.UserID == 0 {
			return nil
		}
		if deps.RollHussars == nil {
			return tg.SendMessage(ctx, in.ChatID, "hussars storage is not configured")
		}
		if err := deps.RollHussars.Delete(ctx, in.UserID); err != nil {
			return err
		}
		return tg.SendMessage(ctx, in.ChatID, "your roll history is deleted")
	}
}

func handleSmileModeOn(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Modes == nil {
			return tg.SendMessage(ctx, in.ChatID, "mode storage is not configured")
		}
		deps.Modes.SetSmile(in.ChatID, true)
		return tg.SendMessage(ctx, in.ChatID, "smile_mode is ON")
	}
}

func handleSmileModeOff(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Modes == nil {
			return tg.SendMessage(ctx, in.ChatID, "mode storage is not configured")
		}
		deps.Modes.SetSmile(in.ChatID, false)
		return tg.SendMessage(ctx, in.ChatID, "smile_mode is OFF")
	}
}

func handleSmileModeStatus(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Modes == nil {
			return tg.SendMessage(ctx, in.ChatID, "mode storage is not configured")
		}
		status := "OFF"
		if deps.Modes.SmileOn(in.ChatID) {
			status = "ON"
		}
		return tg.SendMessage(ctx, in.ChatID, "smile_mode status is "+status)
	}
}

func handleTowelModeOn(deps Dependencies) CommandHandler {
	return modeSetter(deps, "towel_mode", func(chatID int64, on bool) {
		deps.Modes.SetTowel(chatID, on)
	}, true)
}

func handleTowelModeOff(deps Dependencies) CommandHandler {
	return modeSetter(deps, "towel_mode", func(chatID int64, on bool) {
		deps.Modes.SetTowel(chatID, on)
	}, false)
}

func handleTowelModeStatus(deps Dependencies) CommandHandler {
	return modeStatus(deps, "towel_mode", func(chatID int64) bool {
		return deps.Modes.TowelOn(chatID)
	})
}

func handleChatModeOn(deps Dependencies) CommandHandler {
	return modeSetter(deps, "chat_mode", func(chatID int64, on bool) {
		deps.Modes.SetChat(chatID, on)
	}, true)
}

func handleChatModeOff(deps Dependencies) CommandHandler {
	return modeSetter(deps, "chat_mode", func(chatID int64, on bool) {
		deps.Modes.SetChat(chatID, on)
	}, false)
}

func handleChatModeStatus(deps Dependencies) CommandHandler {
	return modeStatus(deps, "chat_mode", func(chatID int64) bool {
		return deps.Modes.ChatOn(chatID)
	})
}

func handleChatNow(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		chatID := in.ChatID
		if chatID == 0 {
			chatID = parseChatID(deps.GroupChatID)
		}
		if chatID == 0 {
			return tg.SendMessage(ctx, in.ChatID, "chat_id is not configured")
		}

		msg := "нян задумчиво смотрит в логи и шепчет: не забудьте писать тесты"
		if deps.ChatGenerator != nil {
			if generated, provider, err := deps.ChatGenerator.Generate(ctx, "short dev reminder for group chat"); err == nil && generated != "" {
				msg = generated + " [" + provider + "]"
			}
		}

		if err := tg.SendMessage(ctx, chatID, msg); err != nil {
			return err
		}

		if in.ChatID != chatID {
			return tg.SendMessage(ctx, in.ChatID, "chat message dispatched")
		}
		return nil
	}
}

func handleFoolsModeOn(deps Dependencies) CommandHandler {
	return modeSetter(deps, "fools_mode", func(chatID int64, on bool) {
		deps.Modes.SetFools(chatID, on)
	}, true)
}

func handleFoolsModeOff(deps Dependencies) CommandHandler {
	return modeSetter(deps, "fools_mode", func(chatID int64, on bool) {
		deps.Modes.SetFools(chatID, on)
	}, false)
}

func handleFoolsModeStatus(deps Dependencies) CommandHandler {
	return modeStatus(deps, "fools_mode", func(chatID int64) bool {
		return deps.Modes.FoolsOn(chatID)
	})
}

func handleNastyaModeOn(deps Dependencies) CommandHandler {
	return modeSetter(deps, "nastya_mode", func(chatID int64, on bool) {
		deps.Modes.SetNastya(chatID, on)
	}, true)
}

func handleNastyaModeOff(deps Dependencies) CommandHandler {
	return modeSetter(deps, "nastya_mode", func(chatID int64, on bool) {
		deps.Modes.SetNastya(chatID, on)
	}, false)
}

func handleNastyaModeStatus(deps Dependencies) CommandHandler {
	return modeStatus(deps, "nastya_mode", func(chatID int64) bool {
		return deps.Modes.NastyaOn(chatID)
	})
}

func modeSetter(deps Dependencies, modeName string, setter func(chatID int64, on bool), on bool) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Modes == nil {
			return tg.SendMessage(ctx, in.ChatID, "mode storage is not configured")
		}
		setter(in.ChatID, on)
		status := "OFF"
		if on {
			status = "ON"
		}
		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("%s is %s", modeName, status))
	}
}

func modeStatus(deps Dependencies, modeName string, getter func(chatID int64) bool) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Modes == nil {
			return tg.SendMessage(ctx, in.ChatID, "mode storage is not configured")
		}
		status := "OFF"
		if getter(in.ChatID) {
			status = "ON"
		}
		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("%s status is %s", modeName, status))
	}
}

func handleZnatoki(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.Buktopuha == nil {
			return tg.SendMessage(ctx, in.ChatID, "buktopuha storage is not configured")
		}
		players, err := deps.Buktopuha.ListAll(ctx)
		if err != nil {
			return err
		}
		if len(players) == 0 {
			return tg.SendMessage(ctx, in.ChatID, "znatoki board is empty")
		}
		lines := []string{"Znatoki BukToPuHy:"}
		for i, p := range players {
			lines = append(lines, fmt.Sprintf("%d) user:%d score:%d wins:%d games:%d", i+1, p.UserID, p.TotalScore, p.WinCounter, p.GameCounter))
			if i >= 9 {
				break
			}
		}
		return tg.SendMessage(ctx, in.ChatID, strings.Join(lines, "\n"))
	}
}

func handleBuktopuha(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.BuktopuhaGame == nil {
			return tg.SendMessage(ctx, in.ChatID, "buktopuha game is not configured")
		}

		word, firstTime := deps.BuktopuhaGame.Start(in.ChatID)
		hint := fmt.Sprintf("Starting BukToPuHa! Guess the word in 30 seconds. It has %d letters.", len(word))
		if !firstTime {
			hint = fmt.Sprintf("New BukToPuHa round! Guess the word in 30 seconds. It has %d letters.", len(word))
		}

		if err := tg.SendMessage(ctx, in.ChatID, hint); err != nil {
			return err
		}

		_, _ = deps.BuktopuhaGame.ActiveWord(in.ChatID)
		return nil
	}
}

func handleAOCStatus(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.AOC == nil {
			return tg.SendMessage(ctx, in.ChatID, "aoc storage is not configured")
		}

		state, ok, err := deps.AOC.Get(ctx)
		if err != nil {
			return err
		}
		if !ok {
			return tg.SendMessage(ctx, in.ChatID, "aoc cache is empty")
		}

		members := countAOCMembers([]byte(state.DataJSON))
		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("aoc cache members: %d", members))
	}
}

func handleAOCRefresh(deps Dependencies) CommandHandler {
	return func(ctx context.Context, in IncomingUpdate, tg TelegramGateway) error {
		if deps.AOC == nil {
			return tg.SendMessage(ctx, in.ChatID, "aoc storage is not configured")
		}
		if strings.TrimSpace(deps.AOCSession) == "" {
			return tg.SendMessage(ctx, in.ChatID, "AOC_SESSION is not configured")
		}

		members, err := refreshAOC(ctx, deps)
		if err != nil {
			return err
		}

		return tg.SendMessage(ctx, in.ChatID, fmt.Sprintf("aoc refreshed, members: %d", members))
	}
}
