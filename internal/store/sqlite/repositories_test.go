package sqlite

import (
	"context"
	"database/sql"
	"testing"
	"time"
)

func newTestDB(t *testing.T) *sql.DB {
	t.Helper()

	db, err := Open(":memory:")
	if err != nil {
		t.Fatalf("open test db: %v", err)
	}

	t.Cleanup(func() {
		_ = db.Close()
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := BootstrapSchema(ctx, db); err != nil {
		t.Fatalf("bootstrap schema: %v", err)
	}

	return db
}

func TestTrustedUsersRepoCRUD(t *testing.T) {
	db := newTestDB(t)
	repo := NewTrustedUsersRepo(db)
	ctx := context.Background()

	trusted, err := repo.IsTrusted(ctx, 42)
	if err != nil {
		t.Fatalf("is trusted (initial): %v", err)
	}
	if trusted {
		t.Fatalf("unexpected trusted=true before insert")
	}

	now := time.Now()
	if err := repo.Upsert(ctx, 42, 7, now); err != nil {
		t.Fatalf("upsert: %v", err)
	}

	user, ok, err := repo.Get(ctx, 42)
	if err != nil {
		t.Fatalf("get: %v", err)
	}
	if !ok {
		t.Fatalf("trusted user not found")
	}
	if user.ByUserID != 7 {
		t.Fatalf("unexpected by_user_id: got=%d want=%d", user.ByUserID, 7)
	}

	trusted, err = repo.IsTrusted(ctx, 42)
	if err != nil {
		t.Fatalf("is trusted (after upsert): %v", err)
	}
	if !trusted {
		t.Fatalf("expected trusted=true after upsert")
	}

	if err := repo.Delete(ctx, 42); err != nil {
		t.Fatalf("delete: %v", err)
	}

	_, ok, err = repo.Get(ctx, 42)
	if err != nil {
		t.Fatalf("get after delete: %v", err)
	}
	if ok {
		t.Fatalf("expected user to be deleted")
	}
}

func TestSinceTopicsRepoUpsertAndList(t *testing.T) {
	db := newTestDB(t)
	repo := NewSinceTopicsRepo(db)
	ctx := context.Background()

	t0 := time.Now().Add(-24 * time.Hour)
	if err := repo.Upsert(ctx, "Go", t0, 1); err != nil {
		t.Fatalf("first upsert: %v", err)
	}
	if err := repo.Upsert(ctx, "go", t0, 1); err != nil {
		t.Fatalf("second upsert: %v", err)
	}

	item, ok, err := repo.Get(ctx, "GO")
	if err != nil {
		t.Fatalf("get topic: %v", err)
	}
	if !ok {
		t.Fatalf("topic not found")
	}
	if item.Topic != "go" {
		t.Fatalf("unexpected topic normalization: got=%q want=%q", item.Topic, "go")
	}
	if item.Count != 2 {
		t.Fatalf("unexpected topic count: got=%d want=%d", item.Count, 2)
	}

	if err := repo.Upsert(ctx, "python", t0, 1); err != nil {
		t.Fatalf("python upsert: %v", err)
	}

	list, err := repo.ListTop(ctx, 10)
	if err != nil {
		t.Fatalf("list top: %v", err)
	}
	if len(list) != 2 {
		t.Fatalf("unexpected list length: got=%d want=%d", len(list), 2)
	}
	if list[0].Topic != "go" {
		t.Fatalf("unexpected first topic ordering: got=%q want=%q", list[0].Topic, "go")
	}
}

func TestPrismWordsRepoIncrementAndList(t *testing.T) {
	db := newTestDB(t)
	repo := NewPrismWordsRepo(db)
	ctx := context.Background()

	now := time.Now()
	if err := repo.Increment(ctx, "Rust", now); err != nil {
		t.Fatalf("increment rust #1: %v", err)
	}
	if err := repo.Increment(ctx, "rust", now); err != nil {
		t.Fatalf("increment rust #2: %v", err)
	}
	if err := repo.Increment(ctx, "go", now); err != nil {
		t.Fatalf("increment go: %v", err)
	}

	words, err := repo.ListAll(ctx)
	if err != nil {
		t.Fatalf("list all: %v", err)
	}
	if len(words) != 2 {
		t.Fatalf("unexpected words length: got=%d want=%d", len(words), 2)
	}
	if words[0].Word != "rust" || words[0].Count != 2 {
		t.Fatalf("unexpected first word: got=%q/%d want=%q/%d", words[0].Word, words[0].Count, "rust", 2)
	}
}
