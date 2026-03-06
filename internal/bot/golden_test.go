package bot

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestHelpGolden(t *testing.T) {
	tg := &fakeTG{}
	if err := handleHelp(context.Background(), IncomingUpdate{ChatID: 1}, tg); err != nil {
		t.Fatalf("help handler: %v", err)
	}
	if len(tg.messages) != 1 {
		t.Fatalf("expected one help message, got=%d", len(tg.messages))
	}

	goldenPath := filepath.Join("testdata", "help.golden")
	golden, err := os.ReadFile(goldenPath)
	if err != nil {
		t.Fatalf("read golden: %v", err)
	}

	want := strings.TrimSuffix(string(golden), "\n")
	if tg.messages[0] != want {
		t.Fatalf("help output mismatch with golden\n--- got ---\n%s\n--- want ---\n%s", tg.messages[0], want)
	}
}
