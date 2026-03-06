package config

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoadRequiresToken(t *testing.T) {
	t.Setenv("TOKEN", "")
	_, err := Load()
	require.Error(t, err)
	assert.Contains(t, err.Error(), "TOKEN")
}

func TestLoadDefaults(t *testing.T) {
	t.Setenv("TOKEN", "test-token-123")
	t.Setenv("SQLITE_DB_PATH", "")
	t.Setenv("DEBUG", "")
	t.Setenv("CHAT_ID", "")

	cfg, err := Load()
	require.NoError(t, err)
	assert.Equal(t, "test-token-123", cfg.Token)
	assert.Equal(t, "bot.db", cfg.SQLiteDBPath)
	assert.False(t, cfg.Debug)
	assert.Empty(t, cfg.GroupChatID)
}

func TestChatID(t *testing.T) {
	cfg := &Config{GroupChatID: "-1001234567890"}
	assert.Equal(t, int64(-1001234567890), cfg.ChatID())

	cfg2 := &Config{GroupChatID: "@vldc_chat"}
	assert.Equal(t, int64(0), cfg2.ChatID())

	cfg3 := &Config{GroupChatID: ""}
	assert.Equal(t, int64(0), cfg3.ChatID())
}
