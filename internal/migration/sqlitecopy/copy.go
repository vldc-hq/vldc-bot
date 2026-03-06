package sqlitecopy

import (
	"context"
	"database/sql"
	"fmt"
)

var tables = []string{
	"trusted_users",
	"buktopuha_players",
	"towel_quarantine",
	"since_topics",
	"roll_hussars",
	"prism_words",
	"peninsula_users",
	"aoc",
}

type Stats struct {
	Copied map[string]int64
}

func CopyAll(ctx context.Context, src *sql.DB, dst *sql.DB) (Stats, error) {
	if src == nil || dst == nil {
		return Stats{}, fmt.Errorf("source and destination db are required")
	}

	stats := Stats{Copied: make(map[string]int64, len(tables))}

	for _, table := range tables {
		if err := ensureTableExists(ctx, src, table); err != nil {
			return Stats{}, err
		}
		if err := ensureTableExists(ctx, dst, table); err != nil {
			return Stats{}, err
		}

		copied, err := copyTable(ctx, src, dst, table)
		if err != nil {
			return Stats{}, err
		}
		stats.Copied[table] = copied
	}

	return stats, nil
}

func ensureTableExists(ctx context.Context, db *sql.DB, table string) error {
	var name string
	err := db.QueryRowContext(ctx, `SELECT name FROM sqlite_master WHERE type='table' AND name=?`, table).Scan(&name)
	if err != nil {
		if err == sql.ErrNoRows {
			return fmt.Errorf("table %q does not exist", table)
		}
		return fmt.Errorf("check table %q: %w", table, err)
	}
	return nil
}

func copyTable(ctx context.Context, src *sql.DB, dst *sql.DB, table string) (int64, error) {
	tx, err := dst.BeginTx(ctx, nil)
	if err != nil {
		return 0, fmt.Errorf("begin destination tx for %q: %w", table, err)
	}

	defer func() {
		_ = tx.Rollback()
	}()

	res, err := tx.ExecContext(ctx, fmt.Sprintf(`INSERT OR REPLACE INTO %s SELECT * FROM main_src.%s`, table, table))
	if err != nil {
		return 0, fmt.Errorf("copy table %q: %w", table, err)
	}

	rows, err := res.RowsAffected()
	if err != nil {
		return 0, fmt.Errorf("rows affected for %q: %w", table, err)
	}

	if err := tx.Commit(); err != nil {
		return 0, fmt.Errorf("commit destination tx for %q: %w", table, err)
	}

	return rows, nil
}

func AttachSource(ctx context.Context, dst *sql.DB, sourcePath string) error {
	if sourcePath == "" {
		return fmt.Errorf("source path is required")
	}
	if _, err := dst.ExecContext(ctx, `ATTACH DATABASE ? AS main_src`, sourcePath); err != nil {
		return fmt.Errorf("attach source db: %w", err)
	}
	return nil
}

func DetachSource(ctx context.Context, dst *sql.DB) error {
	if _, err := dst.ExecContext(ctx, `DETACH DATABASE main_src`); err != nil {
		return fmt.Errorf("detach source db: %w", err)
	}
	return nil
}
