package speech

import (
	"context"
	"fmt"
	"os"
)

type Recognizer interface {
	Recognize(ctx context.Context, telegramFileID string) (string, error)
}

type DisabledRecognizer struct{}

func (DisabledRecognizer) Recognize(context.Context, string) (string, error) {
	return "", fmt.Errorf("speech recognition is disabled")
}

func IsConfigured() bool {
	path := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")
	if path == "" {
		return false
	}
	_, err := os.Stat(path)
	return err == nil
}
