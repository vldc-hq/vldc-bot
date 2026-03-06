package bot

import "testing"

func TestCountAOCMembers(t *testing.T) {
	json := []byte(`{"event":"2026","members":{"1":{"name":"a"},"2":{"name":"b"},"42":{"name":"c"}}}`)
	if got := countAOCMembers(json); got != 3 {
		t.Fatalf("unexpected members count: got=%d want=%d", got, 3)
	}
}

func TestCountAOCMembersInvalidJSON(t *testing.T) {
	if got := countAOCMembers([]byte(`{"members":`)); got != 0 {
		t.Fatalf("expected 0 for invalid json, got=%d", got)
	}
}

func TestCountAOCMembersNoMembers(t *testing.T) {
	if got := countAOCMembers([]byte(`{"event":"2026"}`)); got != 0 {
		t.Fatalf("expected 0 for payload without members, got=%d", got)
	}
}
