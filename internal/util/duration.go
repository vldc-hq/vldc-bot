package util

import (
	"strconv"
	"strings"
	"time"
)

// ParseDuration converts a human-readable duration string like "4w 7d 2h 20m 48s"
// into a time.Duration. Plain numbers without suffix are treated as minutes.
func ParseDuration(raw string) time.Duration {
	var total time.Duration
	for _, part := range strings.Fields(raw) {
		if part == "" {
			continue
		}
		suffix := part[len(part)-1]
		switch suffix {
		case 'w':
			n, err := strconv.Atoi(part[:len(part)-1])
			if err == nil {
				total += time.Duration(n) * 7 * 24 * time.Hour
			}
		case 'd':
			n, err := strconv.Atoi(part[:len(part)-1])
			if err == nil {
				total += time.Duration(n) * 24 * time.Hour
			}
		case 'h':
			n, err := strconv.Atoi(part[:len(part)-1])
			if err == nil {
				total += time.Duration(n) * time.Hour
			}
		case 'm':
			n, err := strconv.Atoi(part[:len(part)-1])
			if err == nil {
				total += time.Duration(n) * time.Minute
			}
		case 's':
			n, err := strconv.Atoi(part[:len(part)-1])
			if err == nil {
				total += time.Duration(n) * time.Second
			}
		default:
			// plain number = minutes
			n, err := strconv.Atoi(part)
			if err == nil {
				total += time.Duration(n) * time.Minute
			}
		}
	}
	return total
}
