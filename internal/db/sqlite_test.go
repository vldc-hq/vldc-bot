package db

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestDB(t *testing.T) *DB {
	t.Helper()
	f, err := os.CreateTemp("", "test_bot_*.db")
	require.NoError(t, err)
	path := f.Name()
	_ = f.Close()
	t.Cleanup(func() { os.Remove(path) })

	d, err := New(path)
	require.NoError(t, err)
	t.Cleanup(func() { _ = d.Close() })
	return d
}

func TestTrustedUsers(t *testing.T) {
	d := newTestDB(t)

	trusted, err := d.IsUserTrusted(123)
	require.NoError(t, err)
	assert.False(t, trusted)

	require.NoError(t, d.TrustUser(123, 999))
	trusted, err = d.IsUserTrusted(123)
	require.NoError(t, err)
	assert.True(t, trusted)

	require.NoError(t, d.UntrustUser(123))
	trusted, err = d.IsUserTrusted(123)
	require.NoError(t, err)
	assert.False(t, trusted)
}

func TestQuarantine(t *testing.T) {
	d := newTestDB(t)

	// Add quarantine user
	require.NoError(t, d.AddQuarantineUser(42, 60))

	u, err := d.FindQuarantineUser(42)
	require.NoError(t, err)
	require.NotNil(t, u)
	assert.Equal(t, int64(42), u.UserID)
	assert.False(t, u.IsExpired())

	// Add related message
	require.NoError(t, d.AddQuarantineRelMessage(42, 100))
	require.NoError(t, d.AddQuarantineRelMessage(42, 101))
	// Dedup
	require.NoError(t, d.AddQuarantineRelMessage(42, 100))

	u, err = d.FindQuarantineUser(42)
	require.NoError(t, err)
	assert.Equal(t, []int{100, 101}, u.MessageIDs())

	// Delete
	require.NoError(t, d.DeleteQuarantineUser(42))
	u, err = d.FindQuarantineUser(42)
	assert.Error(t, err)
	assert.Nil(t, u)

	// Delete all
	require.NoError(t, d.AddQuarantineUser(1, 10))
	require.NoError(t, d.AddQuarantineUser(2, 10))
	require.NoError(t, d.DeleteAllQuarantineUsers())
	users, err := d.FindAllQuarantineUsers()
	require.NoError(t, err)
	assert.Empty(t, users)
}

func TestQuarantineIdempotent(t *testing.T) {
	d := newTestDB(t)

	require.NoError(t, d.AddQuarantineUser(42, 60))
	// Adding again should be no-op
	require.NoError(t, d.AddQuarantineUser(42, 120))

	u, _ := d.FindQuarantineUser(42)
	require.NotNil(t, u)
}

func TestHussars(t *testing.T) {
	d := newTestDB(t)

	// Initially empty
	hussars, err := d.GetAllHussars()
	require.NoError(t, err)
	assert.Empty(t, hussars)

	// Add hussar
	meta := `{"username":"testuser","first_name":"Test"}`
	require.NoError(t, d.AddHussar(123, meta))

	h, err := d.FindHussar(123)
	require.NoError(t, err)
	require.NotNil(t, h)
	assert.Equal(t, "testuser", h.Username())
	assert.Equal(t, 0, h.ShotCounter)

	// Miss
	require.NoError(t, d.HussarMiss(123))
	h, _ = d.FindHussar(123)
	assert.Equal(t, 1, h.ShotCounter)
	assert.Equal(t, 1, h.MissCounter)
	assert.Equal(t, 0, h.DeadCounter)

	// Dead
	require.NoError(t, d.HussarDead(123, 960))
	h, _ = d.FindHussar(123)
	assert.Equal(t, 2, h.ShotCounter)
	assert.Equal(t, 1, h.DeadCounter)
	assert.Equal(t, 960*60, h.TotalTimeInClub)

	// Username fallback
	meta2 := `{"first_name":"John","last_name":"Doe"}`
	require.NoError(t, d.AddHussar(456, meta2))
	h2, _ := d.FindHussar(456)
	assert.Equal(t, "John Doe", h2.Username())

	// Remove
	require.NoError(t, d.RemoveHussar(123))
	_, err = d.FindHussar(123)
	assert.Error(t, err)

	// Wipe
	require.NoError(t, d.RemoveAllHussars())
	hussars, _ = d.GetAllHussars()
	assert.Empty(t, hussars)
}

func TestSinceTopics(t *testing.T) {
	d := newTestDB(t)

	// First mention creates
	require.NoError(t, d.UpsertSinceTopic("golang"))
	topic, err := d.GetSinceTopic("golang")
	require.NoError(t, err)
	assert.Equal(t, 1, topic.Count)

	// Second mention increments
	require.NoError(t, d.UpsertSinceTopic("golang"))
	topic, _ = d.GetSinceTopic("golang")
	assert.Equal(t, 2, topic.Count)

	// List
	require.NoError(t, d.UpsertSinceTopic("rust"))
	topics, err := d.GetAllSinceTopics(10)
	require.NoError(t, err)
	assert.Len(t, topics, 2)
	assert.Equal(t, "golang", topics[0].Topic) // golang has 2, rust has 1
}

func TestPrismWords(t *testing.T) {
	d := newTestDB(t)

	require.NoError(t, d.AddPrismWord("hello"))
	require.NoError(t, d.AddPrismWord("hello"))
	require.NoError(t, d.AddPrismWord("world"))

	words, err := d.GetAllPrismWords()
	require.NoError(t, err)
	assert.Len(t, words, 2)
	assert.Equal(t, "hello", words[0].Word)
	assert.Equal(t, 2, words[0].Count)
}
