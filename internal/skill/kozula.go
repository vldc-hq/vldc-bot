package skill

import (
	"context"
	"encoding/xml"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/util"
)

const (
	cbrURL         = "https://www.cbr.ru/scripts/XML_daily.asp"
	kozulaBaseCost = 15000 // $15k
)

type rateCache struct {
	mu        sync.Mutex
	rate      float64
	fetchedAt time.Time
}

func (rc *rateCache) get() (float64, bool) {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	if time.Since(rc.fetchedAt) < time.Hour && rc.rate > 0 {
		return rc.rate, true
	}
	return 0, false
}

func (rc *rateCache) set(rate float64) {
	rc.mu.Lock()
	defer rc.mu.Unlock()
	rc.rate = rate
	rc.fetchedAt = time.Now()
}

func KozulaSkill() appbot.Skill {
	cache := &rateCache{}

	return appbot.Skill{
		Name: "kozula",
		Hint: "exchange rate",
		Register: func(b *bot.Bot, _ *appbot.Deps) {
			b.RegisterHandler(bot.HandlerTypeMessageText, "/kozula", bot.MatchTypePrefix, func(ctx context.Context, b *bot.Bot, update *models.Update) {
				handleKozula(ctx, b, update, cache)
			})
		},
	}
}

func handleKozula(ctx context.Context, b *bot.Bot, update *models.Update, cache *rateCache) {
	if update.Message == nil {
		return
	}

	rate, ok := cache.get()
	if !ok {
		var err error
		rate, err = fetchUSDRate(ctx)
		if err != nil {
			slog.Error("failed to fetch USD rate", "error", err)
			_, _ = b.SendMessage(ctx, &bot.SendMessageParams{
				ChatID: update.Message.Chat.ID,
				Text:   "Не удалось получить курс ЦБ 😿",
			})
			return
		}
		cache.set(rate)
	}

	rubles := kozulaBaseCost * rate
	text := fmt.Sprintf("💰 Козула-курс:\n\n$1 = %.2f ₽\n$%d = %.0f ₽ (%.0fk ₽)", rate, kozulaBaseCost, rubles, rubles/1000)

	result, _ := b.SendMessage(ctx, &bot.SendMessageParams{
		ChatID: update.Message.Chat.ID,
		Text:   text,
	})
	ids := []int{update.Message.ID, msgID(result)}
	// kozula also cleans the reply-to message
	if update.Message.ReplyToMessage != nil {
		ids = append(ids, update.Message.ReplyToMessage.ID)
	}
	util.ScheduleCleanup(b, update.Message.Chat.ID, 300*time.Second, ids...)
}

type valCurs struct {
	XMLName xml.Name `xml:"ValCurs"`
	Valutes []valute `xml:"Valute"`
}

type valute struct {
	CharCode string `xml:"CharCode"`
	Value    string `xml:"Value"`
	Nominal  int    `xml:"Nominal"`
}

func fetchUSDRate(ctx context.Context) (float64, error) {
	client := &http.Client{Timeout: 10 * time.Second}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, cbrURL, http.NoBody)
	if err != nil {
		return 0, err
	}
	resp, err := client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	var curs valCurs
	if err := xml.Unmarshal(body, &curs); err != nil {
		return 0, err
	}

	for _, v := range curs.Valutes {
		if v.CharCode != "USD" {
			continue
		}
		// CBR uses comma as decimal separator
		valStr := strings.ReplaceAll(v.Value, ",", ".")
		var rate float64
		fmt.Sscanf(valStr, "%f", &rate)
		if v.Nominal > 0 {
			rate /= float64(v.Nominal)
		}
		return rate, nil
	}

	return 0, fmt.Errorf("USD not found in CBR response")
}
