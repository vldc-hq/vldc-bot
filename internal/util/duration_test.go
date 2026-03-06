package util

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestParseDuration(t *testing.T) {
	tests := []struct {
		input    string
		expected time.Duration
	}{
		{"90", 90 * time.Minute},
		{"2h", 2 * time.Hour},
		{"1d", 24 * time.Hour},
		{"1w", 7 * 24 * time.Hour},
		{"30s", 30 * time.Second},
		{"1h 30m", time.Hour + 30*time.Minute},
		{"4w 7d 2h 20m 48s", 4*7*24*time.Hour + 7*24*time.Hour + 2*time.Hour + 20*time.Minute + 48*time.Second},
		{"", 0},
		{"abc", 0},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			assert.Equal(t, tt.expected, ParseDuration(tt.input))
		})
	}
}
