package speech

import (
	"os"
	"path/filepath"
	"testing"
)

func TestIsConfigured(t *testing.T) {
	t.Setenv("GOOGLE_APPLICATION_CREDENTIALS", "")
	if IsConfigured() {
		t.Fatalf("expected not configured when env is empty")
	}

	tmp := filepath.Join(t.TempDir(), "creds.json")
	if err := os.WriteFile(tmp, []byte("{}"), 0o600); err != nil {
		t.Fatalf("write temp creds: %v", err)
	}
	t.Setenv("GOOGLE_APPLICATION_CREDENTIALS", tmp)
	if !IsConfigured() {
		t.Fatalf("expected configured when credentials file exists")
	}
}
