package bot

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"
)

func (r *Runtime) startAOCPolling() {
	if r.deps.AOC == nil || r.deps.AOCSession == "" {
		return
	}

	_, err := r.scheduler.RunRepeating("aoc_update_job", 15*time.Minute, func(ctx context.Context) {
		if _, refreshErr := refreshAOC(ctx, r.deps); refreshErr != nil {
			r.logger.Warn("aoc refresh failed", "error", refreshErr)
		}
	})
	if err != nil {
		r.logger.Warn("failed to start aoc polling", "error", err)
		return
	}

	_, _ = r.scheduler.RunOnce("aoc_update_job_now", 0, func(ctx context.Context) {
		if _, refreshErr := refreshAOC(ctx, r.deps); refreshErr != nil {
			r.logger.Warn("initial aoc refresh failed", "error", refreshErr)
		}
	})
}

func refreshAOC(ctx context.Context, deps Dependencies) (int, error) {
	if deps.AOC == nil {
		return 0, fmt.Errorf("aoc repository is not configured")
	}
	if strings.TrimSpace(deps.AOCSession) == "" {
		return 0, fmt.Errorf("AOC_SESSION is not configured")
	}

	now := time.Now().UTC()
	url := fmt.Sprintf("https://adventofcode.com/%d/leaderboard/private/view/458538.json", now.Year())

	httpTimeout := deps.HTTPTimeout
	if httpTimeout <= 0 {
		httpTimeout = 30 * time.Second
	}
	client := &http.Client{Timeout: httpTimeout}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return 0, fmt.Errorf("build aoc request: %w", err)
	}
	req.Header.Set("User-Agent", "vldc-bot-go-rewrite")
	req.AddCookie(&http.Cookie{Name: "session", Value: deps.AOCSession})

	resp, err := client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("do aoc request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 1024))
		return 0, fmt.Errorf("aoc response status=%d body=%s", resp.StatusCode, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, fmt.Errorf("read aoc response: %w", err)
	}

	members := countAOCMembers(body)
	if err := deps.AOC.Upsert(ctx, string(body)); err != nil {
		return 0, fmt.Errorf("save aoc payload: %w", err)
	}

	return members, nil
}

func countAOCMembers(data []byte) int {
	var payload struct {
		Members map[string]json.RawMessage `json:"members"`
	}
	if err := json.Unmarshal(data, &payload); err != nil {
		return 0
	}
	return len(payload.Members)
}

func parseChatID(chatID string) int64 {
	id, _ := strconv.ParseInt(strings.TrimSpace(chatID), 10, 64)
	return id
}
