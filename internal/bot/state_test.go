package bot

import "testing"

func TestBuktopuhaStateLifecycle(t *testing.T) {
	s := NewBuktopuhaState()

	word, _ := s.Start(1)
	if word == "" {
		t.Fatalf("expected non-empty word")
	}

	if guessed, _, _ := s.Guess(1, "wrong answer"); guessed {
		t.Fatalf("unexpected guess success")
	}

	if guessed, gotWord, score := s.Guess(1, "i think it's "+word); !guessed || gotWord == "" || score <= 0 {
		t.Fatalf("expected successful guess with positive score, got guessed=%v word=%q score=%d", guessed, gotWord, score)
	}

	if _, ok := s.ActiveWord(1); ok {
		t.Fatalf("expected game to stop after successful guess")
	}
}
