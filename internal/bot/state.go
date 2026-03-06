package bot

import (
	"math/rand"
	"strings"
	"sync"
	"time"
)

type ChatModes struct {
	mu     sync.RWMutex
	smile  map[int64]bool
	towel  map[int64]bool
	chat   map[int64]bool
	fools  map[int64]bool
	nastya map[int64]bool
}

func NewChatModes() *ChatModes {
	return &ChatModes{
		smile:  make(map[int64]bool),
		towel:  make(map[int64]bool),
		chat:   make(map[int64]bool),
		fools:  make(map[int64]bool),
		nastya: make(map[int64]bool),
	}
}

func (m *ChatModes) SetSmile(chatID int64, on bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.smile[chatID] = on
}

func (m *ChatModes) SmileOn(chatID int64) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.smile[chatID]
}

func (m *ChatModes) SetTowel(chatID int64, on bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.towel[chatID] = on
}

func (m *ChatModes) TowelOn(chatID int64) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	on, ok := m.towel[chatID]
	if !ok {
		return true
	}
	return on
}

func (m *ChatModes) SetChat(chatID int64, on bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.chat[chatID] = on
}

func (m *ChatModes) ChatOn(chatID int64) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	on, ok := m.chat[chatID]
	if !ok {
		return true
	}
	return on
}

func (m *ChatModes) SetFools(chatID int64, on bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.fools[chatID] = on
}

func (m *ChatModes) FoolsOn(chatID int64) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.fools[chatID]
}

func (m *ChatModes) SetNastya(chatID int64, on bool) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.nastya[chatID] = on
}

func (m *ChatModes) NastyaOn(chatID int64) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()
	on, ok := m.nastya[chatID]
	if !ok {
		return true
	}
	return on
}

type RouletteState struct {
	mu     sync.Mutex
	barrel map[int64][]bool
	rand   *rand.Rand
}

func NewRouletteState() *RouletteState {
	return &RouletteState{barrel: make(map[int64][]bool), rand: rand.New(rand.NewSource(time.Now().UnixNano()))}
}

func (r *RouletteState) Shot(chatID int64) (isShot bool, shotsRemaining int) {
	r.mu.Lock()
	defer r.mu.Unlock()

	barrel := r.barrel[chatID]
	if len(barrel) == 0 {
		barrel = r.reload()
	}

	fate := barrel[len(barrel)-1]
	barrel = barrel[:len(barrel)-1]
	shotsRemaining = len(barrel)

	if fate {
		barrel = r.reload()
	}
	r.barrel[chatID] = barrel

	return fate, shotsRemaining
}

func (r *RouletteState) reload() []bool {
	const bullets = 6
	barrel := make([]bool, bullets)
	barrel[r.rand.Intn(bullets)] = true
	return barrel
}

type BuktopuhaState struct {
	mu      sync.Mutex
	active  map[int64]string
	started map[int64]time.Time
	rand    *rand.Rand
	words   []string
}

func NewBuktopuhaState() *BuktopuhaState {
	return &BuktopuhaState{
		active:  make(map[int64]string),
		started: make(map[int64]time.Time),
		rand:    rand.New(rand.NewSource(time.Now().UnixNano())),
		words: []string{
			"babirusa",
			"pangolin",
			"capybara",
			"platypus",
			"armadillo",
			"axolotl",
			"wombat",
		},
	}
}

func (b *BuktopuhaState) Start(chatID int64) (word string, firstTime bool) {
	b.mu.Lock()
	defer b.mu.Unlock()

	word = b.words[b.rand.Intn(len(b.words))]
	_, active := b.active[chatID]
	b.active[chatID] = word
	b.started[chatID] = time.Now()
	return word, !active
}

func (b *BuktopuhaState) Guess(chatID int64, text string) (guessed bool, word string, score int) {
	b.mu.Lock()
	defer b.mu.Unlock()

	word, ok := b.active[chatID]
	if !ok || word == "" {
		return false, "", 0
	}

	if !strings.Contains(strings.ToLower(text), strings.ToLower(word)) {
		return false, word, 0
	}

	started := b.started[chatID]
	delta := int(time.Since(started).Seconds())
	if delta < 0 {
		delta = 0
	}
	score = 30 - delta + len(word)
	if score < 1 {
		score = 1
	}

	delete(b.active, chatID)
	delete(b.started, chatID)

	return true, word, score
}

func (b *BuktopuhaState) Stop(chatID int64) {
	b.mu.Lock()
	defer b.mu.Unlock()
	delete(b.active, chatID)
	delete(b.started, chatID)
}

func (b *BuktopuhaState) ActiveWord(chatID int64) (string, bool) {
	b.mu.Lock()
	defer b.mu.Unlock()
	word, ok := b.active[chatID]
	return word, ok
}
