package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"sort"
	"time"

	"github.com/vldc-hq/vldc-bot/internal/migration/sqlitecopy"
	storesqlite "github.com/vldc-hq/vldc-bot/internal/store/sqlite"
)

func main() {
	srcPath := os.Getenv("SOURCE_SQLITE_DB_PATH")
	dstPath := os.Getenv("TARGET_SQLITE_DB_PATH")

	if srcPath == "" || dstPath == "" {
		slog.Error("SOURCE_SQLITE_DB_PATH and TARGET_SQLITE_DB_PATH are required")
		os.Exit(1)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	src, err := storesqlite.Open(srcPath)
	if err != nil {
		slog.Error("open source sqlite", "error", err)
		os.Exit(1)
	}
	defer src.Close()

	dst, err := storesqlite.Open(dstPath)
	if err != nil {
		slog.Error("open target sqlite", "error", err)
		os.Exit(1)
	}
	defer dst.Close()

	if err := storesqlite.BootstrapSchema(ctx, dst); err != nil {
		slog.Error("bootstrap target schema", "error", err)
		os.Exit(1)
	}

	if err := sqlitecopy.AttachSource(ctx, dst, srcPath); err != nil {
		slog.Error("attach source db", "error", err)
		os.Exit(1)
	}
	defer func() {
		if err := sqlitecopy.DetachSource(context.Background(), dst); err != nil {
			slog.Warn("detach source db failed", "error", err)
		}
	}()

	stats, err := sqlitecopy.CopyAll(ctx, src, dst)
	if err != nil {
		slog.Error("copy sqlite data", "error", err)
		os.Exit(1)
	}

	tables := make([]string, 0, len(stats.Copied))
	for table := range stats.Copied {
		tables = append(tables, table)
	}
	sort.Strings(tables)

	for _, table := range tables {
		slog.Info(fmt.Sprintf("copied table %s", table), "rows", stats.Copied[table])
	}
}
