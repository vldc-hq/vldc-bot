package ai

import (
	"context"
	"errors"
	"strings"
	"testing"
)

type fakeProvider struct {
	name string
	text string
	err  error
}

func (p fakeProvider) Name() string { return p.name }
func (p fakeProvider) Generate(context.Context, string) (string, error) {
	if p.err != nil {
		return "", p.err
	}
	return p.text, nil
}

func TestFallbackUsesSecondProviderOnFirstFailure(t *testing.T) {
	f, err := NewFallback(
		fakeProvider{name: "gemini", err: errors.New("rate limit")},
		fakeProvider{name: "openai", text: "ok"},
	)
	if err != nil {
		t.Fatalf("new fallback: %v", err)
	}

	text, provider, err := f.Generate(context.Background(), "hello")
	if err != nil {
		t.Fatalf("generate: %v", err)
	}
	if text != "ok" || provider != "openai" {
		t.Fatalf("unexpected result: text=%q provider=%q", text, provider)
	}
}

func TestFallbackReturnsJoinedError(t *testing.T) {
	f, err := NewFallback(
		fakeProvider{name: "gemini", err: errors.New("g-fail")},
		fakeProvider{name: "openai", err: errors.New("o-fail")},
	)
	if err != nil {
		t.Fatalf("new fallback: %v", err)
	}

	_, _, err = f.Generate(context.Background(), "hello")
	if err == nil {
		t.Fatalf("expected joined error")
	}
	msg := err.Error()
	if !strings.Contains(msg, "gemini") || !strings.Contains(msg, "openai") {
		t.Fatalf("unexpected error message: %s", msg)
	}
}
