package translate

import "testing"

func TestIsConfigured(t *testing.T) {
	t.Setenv("GOOGLE_PROJECT_ID", "")
	if IsConfigured() {
		t.Fatalf("expected translator to be not configured")
	}

	t.Setenv("GOOGLE_PROJECT_ID", "my-project")
	if !IsConfigured() {
		t.Fatalf("expected translator to be configured")
	}
}
