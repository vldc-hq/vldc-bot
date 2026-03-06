package ai

import "testing"

func TestHeuristicBioChecker(t *testing.T) {
	c := NewHeuristicBioChecker()

	if c.IsWorthyBio("short bio") {
		t.Fatalf("expected short text to be rejected")
	}
	if c.IsWorthyBio("Я инвестор со стажем, ищу партнеров и быстрый рост") {
		t.Fatalf("expected spam-like text to be rejected")
	}
	if !c.IsWorthyBio("Я backend разработчик, люблю Go, базы данных и open source") {
		t.Fatalf("expected normal bio text to be accepted")
	}
}
