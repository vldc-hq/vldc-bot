package bot

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"testing"
	"time"

	"github.com/vldc-hq/vldc-bot/internal/ai"
	"github.com/vldc-hq/vldc-bot/internal/store"
	storesqlite "github.com/vldc-hq/vldc-bot/internal/store/sqlite"
)

type fakeTG struct {
	messages []string
	banned   []int64
	muted    []string
	unbanned []int64
	deleted  []int
}

func (f *fakeTG) SendMessage(_ context.Context, _ int64, text string) error {
	f.messages = append(f.messages, text)
	return nil
}

func (f *fakeTG) SendMessageWithID(_ context.Context, _ int64, text string) (int, error) {
	f.messages = append(f.messages, text)
	return len(f.messages), nil
}

func (f *fakeTG) BanChatMember(_ context.Context, _ int64, userID int64) error {
	f.banned = append(f.banned, userID)
	return nil
}

func (f *fakeTG) RestrictChatMember(_ context.Context, _ int64, userID int64, minutes int) error {
	f.muted = append(f.muted, fmt.Sprintf("%d:%d", userID, minutes))
	return nil
}

func (f *fakeTG) UnbanChatMember(_ context.Context, _ int64, userID int64) error {
	f.unbanned = append(f.unbanned, userID)
	return nil
}

func (f *fakeTG) DeleteMessage(_ context.Context, _ int64, messageID int) error {
	f.deleted = append(f.deleted, messageID)
	return nil
}

type fakeTrustedRepo struct {
	data map[int64]store.TrustedUser
}

func (r *fakeTrustedRepo) Get(_ context.Context, userID int64) (store.TrustedUser, bool, error) {
	v, ok := r.data[userID]
	return v, ok, nil
}

func (r *fakeTrustedRepo) Upsert(_ context.Context, userID int64, byUserID int64, at time.Time) error {
	if r.data == nil {
		r.data = map[int64]store.TrustedUser{}
	}
	r.data[userID] = store.TrustedUser{UserID: userID, ByUserID: byUserID, At: at}
	return nil
}

func (r *fakeTrustedRepo) Delete(_ context.Context, userID int64) error {
	delete(r.data, userID)
	return nil
}

func (r *fakeTrustedRepo) IsTrusted(_ context.Context, userID int64) (bool, error) {
	_, ok := r.data[userID]
	return ok, nil
}

type fakeSinceRepo struct {
	data map[string]store.SinceTopic
}

func (r *fakeSinceRepo) Get(_ context.Context, topic string) (store.SinceTopic, bool, error) {
	v, ok := r.data[topic]
	return v, ok, nil
}

func (r *fakeSinceRepo) Upsert(_ context.Context, topic string, since time.Time, count int) error {
	if r.data == nil {
		r.data = map[string]store.SinceTopic{}
	}
	current, ok := r.data[topic]
	if ok {
		current.Count++
		current.SinceDateTime = time.Now()
		r.data[topic] = current
		return nil
	}
	r.data[topic] = store.SinceTopic{Topic: topic, SinceDateTime: since, Count: count}
	return nil
}

func (r *fakeSinceRepo) ListTop(_ context.Context, _ int) ([]store.SinceTopic, error) {
	out := make([]store.SinceTopic, 0, len(r.data))
	for _, v := range r.data {
		out = append(out, v)
	}
	return out, nil
}

type fakePrismRepo struct {
	counts map[string]int
}

func (r *fakePrismRepo) Increment(_ context.Context, word string, _ time.Time) error {
	if r.counts == nil {
		r.counts = map[string]int{}
	}
	r.counts[word]++
	return nil
}

func (r *fakePrismRepo) ListAll(_ context.Context) ([]store.PrismWord, error) {
	out := make([]store.PrismWord, 0, len(r.counts))
	for word, count := range r.counts {
		out = append(out, store.PrismWord{Word: word, Count: count, LastUse: time.Now()})
	}
	return out, nil
}

type fakePeninsulaRepo struct {
	items map[int64]store.PeninsulaUser
}

func (r *fakePeninsulaRepo) Upsert(_ context.Context, userID int64, metaJSON string) error {
	if r.items == nil {
		r.items = map[int64]store.PeninsulaUser{}
	}
	r.items[userID] = store.PeninsulaUser{UserID: userID, MetaJSON: metaJSON}
	return nil
}

func (r *fakePeninsulaRepo) ListTop(_ context.Context, limit int) ([]store.PeninsulaUser, error) {
	out := make([]store.PeninsulaUser, 0, len(r.items))
	for _, item := range r.items {
		out = append(out, item)
	}
	if len(out) > limit {
		out = out[:limit]
	}
	return out, nil
}

type fakeAOCRepo struct {
	data string
}

type fakeGenProvider struct {
	name string
	text string
}

func (p fakeGenProvider) Name() string { return p.name }
func (p fakeGenProvider) Generate(context.Context, string) (string, error) {
	return p.text, nil
}

func (r *fakeAOCRepo) Get(context.Context) (store.AOCState, bool, error) {
	if r.data == "" {
		return store.AOCState{}, false, nil
	}
	return store.AOCState{DataJSON: r.data}, true, nil
}

func (r *fakeAOCRepo) Upsert(_ context.Context, dataJSON string) error {
	r.data = dataJSON
	return nil
}

func (r *fakeAOCRepo) DeleteAll(context.Context) error {
	r.data = ""
	return nil
}

func TestTrustAndUntrustHandlers(t *testing.T) {
	repo := &fakeTrustedRepo{data: map[int64]store.TrustedUser{}}
	tg := &fakeTG{}
	deps := Dependencies{TrustedUsers: repo}

	if err := handleTrust(deps)(context.Background(), IncomingUpdate{ChatID: 1, UserID: 100, ReplyToID: 200}, tg); err != nil {
		t.Fatalf("trust: %v", err)
	}
	if _, ok := repo.data[200]; !ok {
		t.Fatalf("expected trusted user to be inserted")
	}

	if err := handleUntrust(deps)(context.Background(), IncomingUpdate{ChatID: 1, UserID: 100, ReplyToID: 200}, tg); err != nil {
		t.Fatalf("untrust: %v", err)
	}
	if _, ok := repo.data[200]; ok {
		t.Fatalf("expected trusted user to be deleted")
	}
}

func TestSinceHandlerCreatesAndIncrements(t *testing.T) {
	repo := &fakeSinceRepo{data: map[string]store.SinceTopic{}}
	tg := &fakeTG{}
	h := handleSince(Dependencies{SinceTopics: repo})

	in := IncomingUpdate{ChatID: 1, Args: []string{"Go", "migration"}}
	if err := h(context.Background(), in, tg); err != nil {
		t.Fatalf("since first call: %v", err)
	}

	key := "go migration"
	row, ok := repo.data[key]
	if !ok {
		t.Fatalf("expected topic to be created")
	}
	if row.Count != 1 {
		t.Fatalf("unexpected count after first call: got=%d want=%d", row.Count, 1)
	}

	if err := h(context.Background(), in, tg); err != nil {
		t.Fatalf("since second call: %v", err)
	}
	if repo.data[key].Count != 2 {
		t.Fatalf("unexpected count after second call: got=%d want=%d", repo.data[key].Count, 2)
	}
}

func TestBanHandler(t *testing.T) {
	tg := &fakeTG{}
	if err := handleBan(context.Background(), IncomingUpdate{ChatID: 10, ReplyToID: 22}, tg); err != nil {
		t.Fatalf("ban handler: %v", err)
	}
	if len(tg.banned) != 1 || tg.banned[0] != 22 {
		t.Fatalf("expected user 22 to be banned, got=%v", tg.banned)
	}
}

func TestMuteHandler(t *testing.T) {
	tg := &fakeTG{}
	if err := handleMute(context.Background(), IncomingUpdate{ChatID: 10, ReplyToID: 22, Args: []string{"15"}}, tg); err != nil {
		t.Fatalf("mute handler: %v", err)
	}
	if len(tg.muted) != 1 || tg.muted[0] != "22:15" {
		t.Fatalf("expected user 22 muted for 15 minutes, got=%v", tg.muted)
	}
}

func TestUnmuteHandler(t *testing.T) {
	tg := &fakeTG{}
	if err := handleUnmute(context.Background(), IncomingUpdate{ChatID: 10, ReplyToID: 22}, tg); err != nil {
		t.Fatalf("unmute handler: %v", err)
	}
	if len(tg.unbanned) != 1 || tg.unbanned[0] != 22 {
		t.Fatalf("expected user 22 unbanned, got=%v", tg.unbanned)
	}
}

func TestPassivePrismTracking(t *testing.T) {
	prism := &fakePrismRepo{counts: map[string]int{}}
	r := &Runtime{deps: Dependencies{PrismWords: prism}}

	r.handlePassiveText(context.Background(), IncomingUpdate{Text: "Go GO /skip Rust", ChatID: 1})

	if prism.counts["go"] != 2 {
		t.Fatalf("unexpected go count: got=%d want=%d", prism.counts["go"], 2)
	}
	if prism.counts["rust"] != 1 {
		t.Fatalf("unexpected rust count: got=%d want=%d", prism.counts["rust"], 1)
	}
	if _, ok := prism.counts["/skip"]; ok {
		t.Fatalf("expected slash-prefixed word to be ignored")
	}
}

func TestVersionHandler(t *testing.T) {
	tg := &fakeTG{}
	err := handleVersion(Dependencies{Version: "1.2.3"})(context.Background(), IncomingUpdate{ChatID: 1}, tg)
	if err != nil {
		t.Fatalf("version handler: %v", err)
	}
	if len(tg.messages) != 1 || !strings.Contains(tg.messages[0], "1.2.3") {
		t.Fatalf("unexpected version output: %v", tg.messages)
	}
}

func TestLengthAndLongestHandlers(t *testing.T) {
	peninsula := &fakePeninsulaRepo{items: map[int64]store.PeninsulaUser{}}
	tg := &fakeTG{}
	deps := Dependencies{Peninsula: peninsula}

	if err := handleLength(deps)(context.Background(), IncomingUpdate{ChatID: 1, UserID: 12345}, tg); err != nil {
		t.Fatalf("length handler: %v", err)
	}
	if len(tg.messages) == 0 || !strings.Contains(tg.messages[len(tg.messages)-1], "length is 5") {
		t.Fatalf("unexpected length message: %v", tg.messages)
	}

	if err := handleLongest(deps)(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("longest handler: %v", err)
	}
	if !strings.Contains(tg.messages[len(tg.messages)-1], "Top known lengths") {
		t.Fatalf("unexpected longest message: %s", tg.messages[len(tg.messages)-1])
	}
}

func TestRollAndWipeHussarsHandlers(t *testing.T) {
	db := newTestDB(t)
	deps := Dependencies{RollHussars: newSQLRollRepo(t, db), Roulette: NewRouletteState()}
	tg := &fakeTG{}

	if err := handleRoll(deps)(context.Background(), IncomingUpdate{ChatID: 1, UserID: 1001, Username: "u"}, tg); err != nil {
		t.Fatalf("roll handler: %v", err)
	}
	if len(tg.messages) == 0 {
		t.Fatalf("expected roll message")
	}

	if err := handleHussars(deps)(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("hussars handler: %v", err)
	}
	if !strings.Contains(tg.messages[len(tg.messages)-1], "Hussars leaderboard") {
		t.Fatalf("unexpected hussars message: %s", tg.messages[len(tg.messages)-1])
	}

	if err := handleWipeHussars(deps)(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("wipe hussars handler: %v", err)
	}
}

func TestBuktopuhaCommandAndGuess(t *testing.T) {
	db := newTestDB(t)
	deps := Dependencies{Buktopuha: newSQLBukRepo(t, db), BuktopuhaGame: NewBuktopuhaState()}
	tg := &fakeTG{}

	if err := handleBuktopuha(deps)(context.Background(), IncomingUpdate{ChatID: 777, UserID: 42, Username: "u"}, tg); err != nil {
		t.Fatalf("buktopuha command: %v", err)
	}

	word, ok := deps.BuktopuhaGame.ActiveWord(777)
	if !ok || word == "" {
		t.Fatalf("expected active buktopuha word")
	}

	r := &Runtime{deps: deps, gw: tg}
	r.handlePassiveText(context.Background(), IncomingUpdate{ChatID: 777, UserID: 42, Username: "u", Text: "maybe " + word})

	if len(tg.messages) == 0 || !strings.Contains(tg.messages[len(tg.messages)-1], "correct!") {
		t.Fatalf("expected success message after guess, got=%v", tg.messages)
	}
}

func TestSmileModeHandlers(t *testing.T) {
	modes := NewChatModes()
	deps := Dependencies{Modes: modes}
	tg := &fakeTG{}

	if err := handleSmileModeOn(deps)(context.Background(), IncomingUpdate{ChatID: 101}, tg); err != nil {
		t.Fatalf("smile on: %v", err)
	}
	if !modes.SmileOn(101) {
		t.Fatalf("expected smile mode to be enabled")
	}

	if err := handleSmileModeStatus(deps)(context.Background(), IncomingUpdate{ChatID: 101}, tg); err != nil {
		t.Fatalf("smile status: %v", err)
	}
	if !strings.Contains(tg.messages[len(tg.messages)-1], "ON") {
		t.Fatalf("unexpected smile status message: %s", tg.messages[len(tg.messages)-1])
	}

	if err := handleSmileModeOff(deps)(context.Background(), IncomingUpdate{ChatID: 101}, tg); err != nil {
		t.Fatalf("smile off: %v", err)
	}
	if modes.SmileOn(101) {
		t.Fatalf("expected smile mode to be disabled")
	}
}

func TestAOCStatusHandler(t *testing.T) {
	tg := &fakeTG{}
	aoc := &fakeAOCRepo{data: `{"members":{"1":{},"2":{}}}`}

	if err := handleAOCStatus(Dependencies{AOC: aoc})(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("aoc status handler: %v", err)
	}
	if len(tg.messages) == 0 || !strings.Contains(tg.messages[len(tg.messages)-1], "members: 2") {
		t.Fatalf("unexpected aoc status message: %v", tg.messages)
	}
}

func TestModerationCommandsBlockedForNonAdmin(t *testing.T) {
	deps := Dependencies{}
	registry, err := NewRegistry(buildCommandSpecs(deps), RequireAdminMiddleware(func(context.Context, IncomingUpdate) (bool, error) {
		return false, nil
	}))
	if err != nil {
		t.Fatalf("new registry: %v", err)
	}

	h, ok := registry.Handler("ban")
	if !ok {
		t.Fatalf("ban handler not found")
	}

	tg := &fakeTG{}
	if err := h(context.Background(), IncomingUpdate{ChatID: 1, ReplyToID: 55}, tg); err != nil {
		t.Fatalf("ban execution: %v", err)
	}
	if len(tg.banned) != 0 {
		t.Fatalf("expected no bans when caller is not admin")
	}
}

func TestExtraModeHandlers(t *testing.T) {
	modes := NewChatModes()
	deps := Dependencies{Modes: modes}
	tg := &fakeTG{}

	if err := handleTowelModeOff(deps)(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("towel off: %v", err)
	}
	if modes.TowelOn(1) {
		t.Fatalf("expected towel mode to be off")
	}

	if err := handleFoolsModeOn(deps)(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("fools on: %v", err)
	}
	if !modes.FoolsOn(1) {
		t.Fatalf("expected fools mode to be on")
	}

	if err := handleNastyaModeOff(deps)(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("nastya off: %v", err)
	}
	if modes.NastyaOn(1) {
		t.Fatalf("expected nastya mode to be off")
	}
}

func TestChatNowUsesGenerator(t *testing.T) {
	fallback, err := ai.NewFallback(fakeGenProvider{name: "g", text: "generated text"})
	if err != nil {
		t.Fatalf("new fallback: %v", err)
	}
	tg := &fakeTG{}
	deps := Dependencies{ChatGenerator: fallback}

	if err := handleChatNow(deps)(context.Background(), IncomingUpdate{ChatID: 55}, tg); err != nil {
		t.Fatalf("chat_now handler: %v", err)
	}
	if len(tg.messages) == 0 || !strings.Contains(tg.messages[len(tg.messages)-1], "generated text") {
		t.Fatalf("unexpected chat_now message: %v", tg.messages)
	}
}

func newTestDB(t *testing.T) *sql.DB {
	t.Helper()

	db, err := storesqlite.Open(":memory:")
	if err != nil {
		t.Fatalf("open sqlite test db: %v", err)
	}

	t.Cleanup(func() {
		_ = db.Close()
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := storesqlite.BootstrapSchema(ctx, db); err != nil {
		t.Fatalf("bootstrap schema: %v", err)
	}

	return db
}

func newSQLRollRepo(t *testing.T, db *sql.DB) store.RollHussarsRepository {
	t.Helper()
	return storesqlite.NewRollHussarsRepo(db)
}

func newSQLBukRepo(t *testing.T, db *sql.DB) store.BuktopuhaRepository {
	t.Helper()
	return storesqlite.NewBuktopuhaRepo(db)
}
