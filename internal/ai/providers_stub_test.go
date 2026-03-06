package ai

import (
	"context"
	"testing"
)

func TestStubProviderRequiresKey(t *testing.T) {
	p := NewOpenAIStub("")
	if _, err := p.Generate(context.Background(), "hello"); err == nil {
		t.Fatalf("expected empty key error")
	}
}

func TestStubProviderGeneratesWithKey(t *testing.T) {
	p := NewGeminiStub("key")
	out, err := p.Generate(context.Background(), "hello")
	if err != nil {
		t.Fatalf("unexpected generate error: %v", err)
	}
	if out == "" {
		t.Fatalf("expected non-empty output")
	}
}
