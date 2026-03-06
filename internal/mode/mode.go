package mode

import (
	"fmt"
	"log/slog"
	"strings"
	"sync"
)

// State tracks which modes are enabled per chat.
type State struct {
	mu       sync.RWMutex
	modes    map[string]*ModeConfig
	chatMode map[string]map[string]bool // chatID -> modeName -> enabled
}

type ModeConfig struct {
	Name        string
	DefaultOn   bool
	OnCallback  func()
	OffCallback func()
}

func NewState() *State {
	return &State{
		modes:    make(map[string]*ModeConfig),
		chatMode: make(map[string]map[string]bool),
	}
}

func (s *State) Register(cfg *ModeConfig) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.modes[cfg.Name] = cfg
}

func (s *State) IsEnabled(chatID int64, modeName string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	key := chatKey(chatID)
	if chatModes, ok := s.chatMode[key]; ok {
		if enabled, exists := chatModes[modeName]; exists {
			return enabled
		}
	}
	// return default
	if cfg, ok := s.modes[modeName]; ok {
		return cfg.DefaultOn
	}
	return false
}

func (s *State) SetEnabled(chatID int64, modeName string, enabled bool) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	cfg, ok := s.modes[modeName]
	if !ok {
		return fmt.Errorf("unknown mode: %s", modeName)
	}

	key := chatKey(chatID)
	if _, ok := s.chatMode[key]; !ok {
		s.chatMode[key] = make(map[string]bool)
	}
	s.chatMode[key][modeName] = enabled

	slog.Info("mode state changed", "mode", modeName, "enabled", enabled, "chat", chatID)

	if enabled && cfg.OnCallback != nil {
		cfg.OnCallback()
	}
	if !enabled && cfg.OffCallback != nil {
		cfg.OffCallback()
	}

	return nil
}

func chatKey(chatID int64) string {
	return fmt.Sprintf("%d", chatID)
}

// StatusText returns human-readable status.
func (s *State) StatusText(chatID int64, modeName string) string {
	if s.IsEnabled(chatID, modeName) {
		return fmt.Sprintf("%s is ON", modeName)
	}
	return fmt.Sprintf("%s is OFF", modeName)
}

// ListModes returns all registered mode names.
func (s *State) ListModes() []string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	names := make([]string, 0, len(s.modes))
	for name := range s.modes {
		names = append(names, name)
	}
	return names
}

// FormatModeCommand returns the expected command names for a mode.
func FormatModeCommand(modeName, action string) string {
	return strings.ToLower(modeName) + "_" + action
}
