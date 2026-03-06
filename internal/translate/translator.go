package translate

import (
	"context"
	"fmt"
	"os"
)

type Translator interface {
	Translate(ctx context.Context, text string, sourceLang string, targetLang string) (string, error)
}

type DisabledTranslator struct{}

func (DisabledTranslator) Translate(context.Context, string, string, string) (string, error) {
	return "", fmt.Errorf("translation is disabled")
}

func IsConfigured() bool {
	return os.Getenv("GOOGLE_PROJECT_ID") != ""
}
