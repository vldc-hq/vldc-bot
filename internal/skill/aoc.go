package skill

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"time"

	"github.com/go-telegram/bot"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
)

const (
	aocFetchInterval = 15 * time.Minute
	aocBaseURL       = "https://adventofcode.com"
	aocLeaderboard   = "458538"
)

type aocMember struct {
	Name               string                        `json:"name"`
	Stars              int                           `json:"stars"`
	CompletionDayLevel map[string]map[string]aocStar `json:"completion_day_level"`
}

type aocStar struct {
	GetStarTS json.Number `json:"get_star_ts"`
}

type aocLeaderboardData struct {
	Members map[string]aocMember `json:"members"`
}

func AocSkill() appbot.Skill {
	return appbot.Skill{
		Name: "aoc_mode",
		Hint: "Advent of Code tracker",
		Register: func(b *bot.Bot, deps *appbot.Deps) {
			if deps.Config.AOCSession == "" {
				slog.Info("aoc_mode: AOC_SESSION not set, skipping")
				return
			}
			go runAocTracker(b, deps)
		},
	}
}

func runAocTracker(b *bot.Bot, deps *appbot.Deps) {
	ticker := time.NewTicker(aocFetchInterval)
	defer ticker.Stop()

	// Initial fetch
	checkAoc(b, deps)

	for range ticker.C {
		checkAoc(b, deps)
	}
}

func checkAoc(b *bot.Bot, deps *appbot.Deps) {
	now := time.Now().UTC()
	if now.Month() != time.December {
		return
	}

	year := now.Year()
	day := aocDay(now)
	if day < 1 || day > 25 {
		return
	}

	data, err := fetchAocLeaderboard(year, deps.Config.AOCSession)
	if err != nil {
		slog.Error("aoc: failed to fetch leaderboard", "error", err)
		return
	}

	cached, _ := deps.DB.GetAOCData()
	var cachedData aocLeaderboardData
	if cached != "" {
		_ = json.Unmarshal([]byte(cached), &cachedData)
	}

	newJSON, _ := json.Marshal(data)
	_ = deps.DB.SetAOCData(string(newJSON))

	chatID := deps.Config.ChatID()
	if chatID == 0 {
		return
	}

	notifications := findNewCompletions(cachedData, *data, day)
	ctx := context.Background()
	for _, n := range notifications {
		_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
			ChatID: chatID,
			Text:   n,
		})
	}
}

func aocDay(t time.Time) int {
	// AoC puzzles release at 05:00 UTC (00:00 EST)
	start := time.Date(t.Year(), time.December, 1, 5, 0, 0, 0, time.UTC)
	if t.Before(start) {
		return 0
	}
	return int(t.Sub(start).Hours()/24) + 1
}

func fetchAocLeaderboard(year int, session string) (*aocLeaderboardData, error) {
	url := fmt.Sprintf("%s/%d/leaderboard/private/view/%s.json", aocBaseURL, year, aocLeaderboard)

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, http.NoBody)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Cookie", "session="+session)

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var data aocLeaderboardData
	if err := json.Unmarshal(body, &data); err != nil {
		return nil, err
	}

	return &data, nil
}

func findNewCompletions(cached, current aocLeaderboardData, currentDay int) []string {
	dayStr := strconv.Itoa(currentDay)

	// Check if anyone already solved both parts in cached data
	cachedHasBothParts := false
	for _, member := range cached.Members {
		if dayLevel, ok := member.CompletionDayLevel[dayStr]; ok {
			if _, has2 := dayLevel["2"]; has2 {
				cachedHasBothParts = true
				break
			}
		}
	}

	// If someone already solved both parts before, no new notification
	if cachedHasBothParts {
		return nil
	}

	// Find the first person who solved both parts (by part2 timestamp)
	var bestMemberID string
	var bestTS int64
	for memberID, member := range current.Members {
		dayLevel, ok := member.CompletionDayLevel[dayStr]
		if !ok {
			continue
		}
		part2, hasPart2 := dayLevel["2"]
		if !hasPart2 {
			continue
		}
		ts, _ := part2.GetStarTS.Int64()
		if bestMemberID == "" || ts < bestTS {
			bestMemberID = memberID
			bestTS = ts
		}
	}

	if bestMemberID == "" {
		return nil
	}

	member := current.Members[bestMemberID]
	name := member.Name
	if name == "" {
		name = "Anonymous #" + bestMemberID
	}

	solveTime := formatSolveTime(bestTS, currentDay)
	return []string{fmt.Sprintf(
		"Wow! @%s just solves Day %d problem in %s, gaining %d ⭐️! Gut Gemacht! 🔥🔥🔥",
		name, currentDay, solveTime, member.Stars,
	)}
}

func formatSolveTime(ts int64, day int) string {
	if ts == 0 {
		return "unknown"
	}
	solveAt := time.Unix(ts, 0).UTC()
	puzzleStart := time.Date(solveAt.Year(), time.December, day, 5, 0, 0, 0, time.UTC)
	d := solveAt.Sub(puzzleStart)
	if d < 0 {
		return "unknown"
	}
	h := int(d.Hours())
	m := int(d.Minutes()) % 60
	s := int(d.Seconds()) % 60
	return fmt.Sprintf("%dh %dm %ds", h, m, s)
}
