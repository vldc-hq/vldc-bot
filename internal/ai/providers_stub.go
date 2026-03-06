package ai

import (
	"context"
	"fmt"
	"strings"
)

type StubProvider struct {
	name string
	key  string
}

func NewOpenAIStub(apiKey string) *StubProvider {
	return &StubProvider{name: "openai", key: strings.TrimSpace(apiKey)}
}

func NewGeminiStub(apiKey string) *StubProvider {
	return &StubProvider{name: "gemini", key: strings.TrimSpace(apiKey)}
}

func (p *StubProvider) Name() string {
	return p.name
}

func (p *StubProvider) Generate(context.Context, string) (string, error) {
	if p.key == "" {
		return "", fmt.Errorf("api key is empty")
	}
	if p.name == "openai" {
		return "chat-mode ping: write tests before merge", nil
	}
	return "chat-mode ping: ship small and iterate", nil
}
