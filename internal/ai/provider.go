package ai

import (
	"context"
	"errors"
	"fmt"
)

type Provider interface {
	Name() string
	Generate(ctx context.Context, prompt string) (string, error)
}

type Fallback struct {
	providers []Provider
}

func NewFallback(providers ...Provider) (*Fallback, error) {
	filtered := make([]Provider, 0, len(providers))
	for _, p := range providers {
		if p != nil {
			filtered = append(filtered, p)
		}
	}
	if len(filtered) == 0 {
		return nil, fmt.Errorf("at least one provider is required")
	}
	return &Fallback{providers: filtered}, nil
}

func (f *Fallback) Generate(ctx context.Context, prompt string) (string, string, error) {
	var errs []error
	for _, p := range f.providers {
		text, err := p.Generate(ctx, prompt)
		if err == nil {
			return text, p.Name(), nil
		}
		errs = append(errs, fmt.Errorf("%s: %w", p.Name(), err))
	}
	return "", "", errors.Join(errs...)
}
