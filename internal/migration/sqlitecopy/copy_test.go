package sqlitecopy

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	storesqlite "github.com/vldc-hq/vldc-bot/internal/store/sqlite"
)

func TestCopyAll(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	srcPath := filepath.Join(t.TempDir(), "src.db")
	dstPath := filepath.Join(t.TempDir(), "dst.db")

	src, err := storesqlite.Open(srcPath)
	if err != nil {
		t.Fatalf("open src: %v", err)
	}
	t.Cleanup(func() { _ = src.Close() })

	dst, err := storesqlite.Open(dstPath)
	if err != nil {
		t.Fatalf("open dst: %v", err)
	}
	t.Cleanup(func() { _ = dst.Close() })

	if err := storesqlite.BootstrapSchema(ctx, src); err != nil {
		t.Fatalf("bootstrap src: %v", err)
	}
	if err := storesqlite.BootstrapSchema(ctx, dst); err != nil {
		t.Fatalf("bootstrap dst: %v", err)
	}

	if _, err := src.ExecContext(ctx, `INSERT INTO trusted_users (user_id, "by", datetime) VALUES (100, 42, datetime('now'))`); err != nil {
		t.Fatalf("seed src trusted_users: %v", err)
	}
	if _, err := src.ExecContext(ctx, `INSERT INTO since_topics (topic, since_datetime, count) VALUES ('golang', datetime('now'), 5)`); err != nil {
		t.Fatalf("seed src since_topics: %v", err)
	}

	if err := AttachSource(ctx, dst, srcPath); err != nil {
		t.Fatalf("attach src: %v", err)
	}
	t.Cleanup(func() { _ = DetachSource(context.Background(), dst) })

	stats, err := CopyAll(ctx, src, dst)
	if err != nil {
		t.Fatalf("copy all: %v", err)
	}
	if stats.Copied["trusted_users"] != 1 {
		t.Fatalf("unexpected trusted_users copied rows: %d", stats.Copied["trusted_users"])
	}

	var count int
	if err := dst.QueryRowContext(ctx, `SELECT COUNT(*) FROM trusted_users WHERE user_id=100`).Scan(&count); err != nil {
		t.Fatalf("count trusted users in dst: %v", err)
	}
	if count != 1 {
		t.Fatalf("expected copied trusted user in destination")
	}
}
