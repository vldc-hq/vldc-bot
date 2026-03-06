package ai

import "strings"

type BioChecker interface {
	IsWorthyBio(text string) bool
}

type HeuristicBioChecker struct{}

func NewHeuristicBioChecker() HeuristicBioChecker {
	return HeuristicBioChecker{}
}

func (HeuristicBioChecker) IsWorthyBio(text string) bool {
	t := strings.ToLower(strings.TrimSpace(text))
	if len(t) < 15 {
		return false
	}

	spamMarkers := []string{
		"crypto",
		"инвест",
		"партнер",
		"прибыль",
		"реклама",
		"казино",
		"ставки",
	}
	for _, marker := range spamMarkers {
		if strings.Contains(t, marker) {
			return false
		}
	}

	return true
}
