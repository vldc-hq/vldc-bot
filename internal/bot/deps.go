package bot

import (
	"time"

	"github.com/vldc-hq/vldc-bot/internal/ai"
	"github.com/vldc-hq/vldc-bot/internal/speech"
	"github.com/vldc-hq/vldc-bot/internal/store"
	"github.com/vldc-hq/vldc-bot/internal/translate"
)

type Dependencies struct {
	Version       string
	HTTPTimeout   time.Duration
	AOCSession    string
	GroupChatID   string
	TrustedUsers  store.TrustedUsersRepository
	SinceTopics   store.SinceTopicsRepository
	PrismWords    store.PrismWordsRepository
	Peninsula     store.PeninsulaRepository
	RollHussars   store.RollHussarsRepository
	AOC           store.AOCRepository
	Quarantine    store.QuarantineRepository
	Buktopuha     store.BuktopuhaRepository
	Modes         *ChatModes
	Roulette      *RouletteState
	BuktopuhaGame *BuktopuhaState
	BioChecker    ai.BioChecker
	ChatGenerator *ai.Fallback
	Speech        speech.Recognizer
	Translator    translate.Translator
}
