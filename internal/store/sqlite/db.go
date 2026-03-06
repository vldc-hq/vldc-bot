package sqlite

import (
	"context"
	"database/sql"
	"fmt"
	"strings"
	"time"

	_ "modernc.org/sqlite"
)

func Open(path string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("open sqlite db: %w", err)
	}

	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)
	db.SetConnMaxLifetime(0)

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("ping sqlite db: %w", err)
	}

	return db, nil
}

func BootstrapSchema(ctx context.Context, db *sql.DB) error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS trusted_users (
			user_id INTEGER PRIMARY KEY,
			"by" INTEGER,
			datetime DATETIME
		)`,
		`CREATE TABLE IF NOT EXISTS buktopuha_players (
			user_id INTEGER PRIMARY KEY,
			meta TEXT,
			game_counter INTEGER DEFAULT 0,
			win_counter INTEGER DEFAULT 0,
			total_score INTEGER DEFAULT 0,
			created_at DATETIME,
			updated_at DATETIME
		)`,
		`CREATE TABLE IF NOT EXISTS towel_quarantine (
			user_id INTEGER PRIMARY KEY,
			rel_messages TEXT,
			datetime DATETIME
		)`,
		`CREATE TABLE IF NOT EXISTS since_topics (
			topic TEXT PRIMARY KEY,
			since_datetime DATETIME,
			count INTEGER DEFAULT 0
		)`,
		`CREATE TABLE IF NOT EXISTS roll_hussars (
			user_id INTEGER PRIMARY KEY,
			meta TEXT,
			shot_counter INTEGER DEFAULT 0,
			miss_counter INTEGER DEFAULT 0,
			dead_counter INTEGER DEFAULT 0,
			total_time_in_club INTEGER DEFAULT 0,
			first_shot DATETIME,
			last_shot DATETIME
		)`,
		`CREATE TABLE IF NOT EXISTS prism_words (
			word TEXT PRIMARY KEY,
			count INTEGER DEFAULT 0,
			last_use DATETIME
		)`,
		`CREATE TABLE IF NOT EXISTS peninsula_users (
			user_id INTEGER PRIMARY KEY,
			meta TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS aoc (
			id INTEGER PRIMARY KEY CHECK (id = 0),
			data TEXT
		)`,
	}

	for _, q := range queries {
		if _, err := db.ExecContext(ctx, q); err != nil {
			return fmt.Errorf("bootstrap schema failed for query %q: %w", shortQuery(q), err)
		}
	}

	return nil
}

func withTx(ctx context.Context, db *sql.DB, fn func(tx *sql.Tx) error) error {
	tx, err := db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("begin tx: %w", err)
	}

	if err := fn(tx); err != nil {
		_ = tx.Rollback()
		return err
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("commit tx: %w", err)
	}

	return nil
}

func shortQuery(q string) string {
	q = strings.TrimSpace(q)
	if len(q) <= 80 {
		return q
	}
	return q[:80] + "..."
}
