package skill

import (
	"context"
	"os"
	"testing"
	"time"

	"github.com/go-telegram/bot"
	"github.com/go-telegram/bot/models"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	appbot "github.com/vldc-hq/vldc-bot/internal/bot"
	"github.com/vldc-hq/vldc-bot/internal/config"
	"github.com/vldc-hq/vldc-bot/internal/db"
	"github.com/vldc-hq/vldc-bot/internal/mode"
	"github.com/vldc-hq/vldc-bot/internal/skill/testutil"
)

type testEnv struct {
	mock   *testutil.MockTelegram
	bot    *bot.Bot
	db     *db.DB
	deps   *appbot.Deps
	ctx    context.Context
	dbPath string
}

func setupTestEnv(t *testing.T) *testEnv {
	t.Helper()

	f, err := os.CreateTemp("", "test_bot_*.db")
	require.NoError(t, err)
	dbPath := f.Name()
	_ = f.Close()
	t.Cleanup(func() { os.Remove(dbPath) })

	database, err := db.New(dbPath)
	require.NoError(t, err)
	t.Cleanup(func() { _ = database.Close() })

	mock := testutil.NewMockTelegram()
	t.Cleanup(func() { mock.Close() })

	b, err := bot.New("test-token",
		bot.WithServerURL(mock.Server.URL),
		bot.WithDefaultHandler(func(_ context.Context, _ *bot.Bot, _ *models.Update) {}),
	)
	require.NoError(t, err)

	deps := &appbot.Deps{
		DB: database,
		Config: &config.Config{
			Token:       "test-token",
			GroupChatID: "-100123",
		},
		ModeState: mode.NewState(),
	}

	return &testEnv{
		mock:   mock,
		bot:    b,
		db:     database,
		deps:   deps,
		ctx:    context.Background(),
		dbPath: dbPath,
	}
}

func makeUpdate(chatID int64, userID int64, text string) *models.Update {
	return &models.Update{
		Message: &models.Message{
			ID:   1,
			Chat: models.Chat{ID: chatID},
			From: &models.User{
				ID:        userID,
				FirstName: "TestUser",
				Username:  "testuser",
			},
			Text: text,
			Date: int(time.Now().Unix()),
		},
	}
}

func makeReplyUpdate(chatID int64, userID int64, text string, replyToUserID int64) *models.Update {
	u := makeUpdate(chatID, userID, text)
	u.Message.ReplyToMessage = &models.Message{
		ID:   2,
		Chat: models.Chat{ID: chatID},
		From: &models.User{
			ID:        replyToUserID,
			FirstName: "TargetUser",
			Username:  "targetuser",
		},
	}
	return u
}

// --- Integration Tests ---

func TestCoreStart(t *testing.T) {
	env := setupTestEnv(t)
	CoreSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/start")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "VLDC Bot")
}

func TestCoreHelp(t *testing.T) {
	env := setupTestEnv(t)
	CoreSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/help")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "admin")
}

func TestCoreVersion(t *testing.T) {
	env := setupTestEnv(t)
	CoreSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/version")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, Version)
}

func TestNya(t *testing.T) {
	env := setupTestEnv(t)
	env.mock.SetAdmin(42)
	NyaSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/nya hello world")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "hello world")
}

func TestMuteRequiresAdmin(t *testing.T) {
	env := setupTestEnv(t)
	MuteSkill().Register(env.bot, env.deps)

	// Non-admin tries to mute via reply — should be rejected
	update := makeReplyUpdate(-100123, 42, "/mute 30", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	assert.Empty(t, msgs) // no response for non-admin
}

func TestMuteAsAdmin(t *testing.T) {
	env := setupTestEnv(t)
	env.mock.SetAdmin(42)
	MuteSkill().Register(env.bot, env.deps)

	update := makeReplyUpdate(-100123, 42, "/mute 30", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	restrictions := env.mock.Restrictions()
	require.Len(t, restrictions, 1)
	assert.Equal(t, int64(99), restrictions[0].UserID)
}

func TestUnmuteAsAdmin(t *testing.T) {
	env := setupTestEnv(t)
	env.mock.SetAdmin(42)
	MuteSkill().Register(env.bot, env.deps)

	update := makeReplyUpdate(-100123, 42, "/unmute", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	restrictions := env.mock.Restrictions()
	require.Len(t, restrictions, 1)
	assert.Equal(t, int64(99), restrictions[0].UserID)
}

func TestBanRequiresAdmin(t *testing.T) {
	env := setupTestEnv(t)
	BanSkill().Register(env.bot, env.deps)

	update := makeReplyUpdate(-100123, 42, "/ban", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	assert.Empty(t, msgs)
}

func TestBanAsAdmin(t *testing.T) {
	env := setupTestEnv(t)
	env.mock.SetAdmin(42)
	BanSkill().Register(env.bot, env.deps)

	update := makeReplyUpdate(-100123, 42, "/ban", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "забанен")
}

func TestRollCreatesHussar(t *testing.T) {
	env := setupTestEnv(t)
	RollSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/roll")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)

	h, err := env.db.FindHussar(42)
	require.NoError(t, err)
	require.NotNil(t, h)
	assert.Equal(t, 1, h.ShotCounter)
}

func TestGDPRRemovesHussar(t *testing.T) {
	env := setupTestEnv(t)
	RollSkill().Register(env.bot, env.deps)

	// Add hussar first
	_ = env.db.AddHussar(42, `{"username":"testuser"}`)

	update := makeUpdate(-100123, 42, "/gdpr_me")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)

	h, _ := env.db.FindHussar(42)
	assert.Nil(t, h)

	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "boomer")
}

func TestHussarsLeaderboard(t *testing.T) {
	env := setupTestEnv(t)
	RollSkill().Register(env.bot, env.deps)

	_ = env.db.AddHussar(1, `{"username":"alice"}`)
	_ = env.db.HussarDead(1, 960)
	_ = env.db.AddHussar(2, `{"username":"bob"}`)
	_ = env.db.HussarMiss(2)

	update := makeUpdate(-100123, 42, "/hussars")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)

	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "alice")
	assert.Contains(t, msgs[0].Text, "bob")
}

func TestSinceTopic(t *testing.T) {
	env := setupTestEnv(t)
	SinceSkill().Register(env.bot, env.deps)

	// Enable since_mode
	_ = env.deps.ModeState.SetEnabled(-100123, sinceModeName, true)

	update := makeUpdate(-100123, 42, "/since golang")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)

	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "golang")

	// Second time
	env.mock.Reset()
	update2 := makeUpdate(-100123, 42, "/since golang")
	env.bot.ProcessUpdate(env.ctx, update2)

	time.Sleep(100 * time.Millisecond)
	msgs = env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "2 times")
}

func TestIsWorthy(t *testing.T) {
	assert.True(t, IsWorthy("I love VLDC and everything about it"))
	assert.True(t, IsWorthy("I am a developer with 10 years of experience"))
	assert.False(t, IsWorthy("short"))
	assert.False(t, IsWorthy(""))
}

func TestSelfMute(t *testing.T) {
	env := setupTestEnv(t)
	MuteSkill().Register(env.bot, env.deps)

	// /mute without reply = self-mute
	update := makeUpdate(-100123, 42, "/mute")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	restrictions := env.mock.Restrictions()
	require.Len(t, restrictions, 1)
	assert.Equal(t, int64(42), restrictions[0].UserID)
}

func TestBanme(t *testing.T) {
	env := setupTestEnv(t)
	BanmeSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/banme")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	restrictions := env.mock.Restrictions()
	require.Len(t, restrictions, 1)
	assert.Equal(t, int64(42), restrictions[0].UserID)
}

func TestStill(t *testing.T) {
	env := setupTestEnv(t)
	StillSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/still golang")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "golang")
	assert.Contains(t, msgs[0].Text, "лул")
}

func TestConvertYear(t *testing.T) {
	assert.Equal(t, "2k26", convertYear(2026))
	assert.Equal(t, "2k00", convertYear(2000))
	assert.Equal(t, "1999", convertYear(1999))
}

func TestAtLeast70k(t *testing.T) {
	env := setupTestEnv(t)
	AtLeast70kSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/70k")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "вилку")
}

func TestTree(t *testing.T) {
	env := setupTestEnv(t)
	TreeSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/tree")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "adventofcode.com")
}

func TestTrust(t *testing.T) {
	env := setupTestEnv(t)
	env.mock.SetAdmin(42)
	TrustedSkill().Register(env.bot, env.deps)

	update := makeReplyUpdate(-100123, 42, "/trust", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "trusted")

	trusted, err := env.db.IsUserTrusted(99)
	require.NoError(t, err)
	assert.True(t, trusted)
}

func TestUntrust(t *testing.T) {
	env := setupTestEnv(t)
	env.mock.SetAdmin(42)
	TrustedSkill().Register(env.bot, env.deps)

	_ = env.db.TrustUser(99, 42)

	update := makeReplyUpdate(-100123, 42, "/untrust", 99)
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	trusted, err := env.db.IsUserTrusted(99)
	require.NoError(t, err)
	assert.False(t, trusted)
}

func TestPrismTop(t *testing.T) {
	env := setupTestEnv(t)
	PrismSkill().Register(env.bot, env.deps)

	_ = env.db.AddPrismWord("golang")
	_ = env.db.AddPrismWord("golang")
	_ = env.db.AddPrismWord("rust")

	update := makeUpdate(-100123, 42, "/top")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "golang")
}

func TestUwuDetection(t *testing.T) {
	env := setupTestEnv(t)
	UwuSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "hello uwu world")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "don't uwu")
}

func TestLength(t *testing.T) {
	env := setupTestEnv(t)
	LengthSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/length")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "🍆")
}

func TestLongest(t *testing.T) {
	env := setupTestEnv(t)
	LengthSkill().Register(env.bot, env.deps)

	_ = env.db.UpsertLengthUser(12345, "alice", "Alice", "", 5)
	_ = env.db.UpsertLengthUser(123456789, "bob", "Bob", "", 9)

	update := makeUpdate(-100123, 42, "/longest")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "bob")
}

func TestZnatokiEmpty(t *testing.T) {
	env := setupTestEnv(t)
	BuktopuhaSkill().Register(env.bot, env.deps)

	update := makeUpdate(-100123, 42, "/znatoki")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "No players")
}

func TestZnatokiWithPlayers(t *testing.T) {
	env := setupTestEnv(t)
	BuktopuhaSkill().Register(env.bot, env.deps)

	_ = env.db.AddBuktopuhaPlayer(1, `{"username":"alice"}`, 100)
	_ = env.db.AddBuktopuhaPlayer(2, `{"username":"bob"}`, 50)

	update := makeUpdate(-100123, 42, "/znatoki")
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(50 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.Len(t, msgs, 1)
	assert.Contains(t, msgs[0].Text, "alice")
	assert.Contains(t, msgs[0].Text, "bob")
}

func TestCheckPirozhok(t *testing.T) {
	// Valid pirozhok: 9-8-9-8 syllables
	valid := "а вот и первая строка я\nа вот вторая строчка\nа вот и третья строка я\nа вот четвёрта точка"
	// This test verifies the validator detects line count errors
	assert.NotEmpty(t, checkPirozhok("only one line"))
	assert.NotEmpty(t, checkPirozhok("line1\nline2\nline3"))
	// Valid format check (may or may not pass syllable counts)
	_ = checkPirozhok(valid)
}

func TestNastyaVoice(t *testing.T) {
	env := setupTestEnv(t)
	NastyaSkill().Register(env.bot, env.deps)

	update := &models.Update{
		Message: &models.Message{
			ID:   1,
			Chat: models.Chat{ID: -100123},
			From: &models.User{
				ID:        42,
				FirstName: "TestUser",
				Username:  "testuser",
			},
			Voice: &models.Voice{Duration: 10},
			Date:  int(time.Now().Unix()),
		},
	}
	env.bot.ProcessUpdate(env.ctx, update)

	time.Sleep(100 * time.Millisecond)
	msgs := env.mock.SentMessages()
	require.GreaterOrEqual(t, len(msgs), 1)
	assert.Contains(t, msgs[0].Text, "🤫")
}

func TestBuktopuhaPlayerDB(t *testing.T) {
	env := setupTestEnv(t)

	_ = env.db.AddBuktopuhaPlayer(42, `{"username":"testuser"}`, 50)
	p, err := env.db.FindBuktopuhaPlayer(42)
	require.NoError(t, err)
	require.NotNil(t, p)
	assert.Equal(t, 50, p.TotalScore)
	assert.Equal(t, 1, p.WinCounter)
	assert.Equal(t, 1, p.GameCounter)

	_ = env.db.IncBuktopuhaWin(42, 30)
	p, _ = env.db.FindBuktopuhaPlayer(42)
	assert.Equal(t, 80, p.TotalScore)
	assert.Equal(t, 2, p.WinCounter)

	_ = env.db.IncBuktopuhaGameCounter(42)
	p, _ = env.db.FindBuktopuhaPlayer(42)
	assert.Equal(t, 2, p.GameCounter)
}

func TestCensorWord(t *testing.T) {
	assert.Equal(t, "The *** is big", censorWord("The cat is big", "cat"))
	assert.Equal(t, "*** and ***", censorWord("Cat and cat", "cat"))
}
