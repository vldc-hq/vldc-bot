package bot

import (
	"context"
	"fmt"
	"sync"
	"time"
)

type CancelFunc func()

type Scheduler interface {
	RunRepeating(name string, interval time.Duration, fn func(context.Context)) (CancelFunc, error)
	RunOnce(name string, after time.Duration, fn func(context.Context)) (CancelFunc, error)
	Cancel(name string)
}

type LocalScheduler struct {
	mu      sync.Mutex
	cancels map[string]context.CancelFunc
}

func NewLocalScheduler() *LocalScheduler {
	return &LocalScheduler{cancels: make(map[string]context.CancelFunc)}
}

func (s *LocalScheduler) RunRepeating(name string, interval time.Duration, fn func(context.Context)) (CancelFunc, error) {
	if name == "" {
		return nil, fmt.Errorf("job name must not be empty")
	}
	if interval <= 0 {
		return nil, fmt.Errorf("interval must be > 0")
	}
	if fn == nil {
		return nil, fmt.Errorf("job callback must not be nil")
	}

	s.Cancel(name)

	ctx, cancel := context.WithCancel(context.Background())
	ticker := time.NewTicker(interval)

	s.mu.Lock()
	s.cancels[name] = func() {
		cancel()
		ticker.Stop()
	}
	s.mu.Unlock()

	go func() {
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				fn(ctx)
			}
		}
	}()

	return func() { s.Cancel(name) }, nil
}

func (s *LocalScheduler) RunOnce(name string, after time.Duration, fn func(context.Context)) (CancelFunc, error) {
	if name == "" {
		return nil, fmt.Errorf("job name must not be empty")
	}
	if after < 0 {
		return nil, fmt.Errorf("after must be >= 0")
	}
	if fn == nil {
		return nil, fmt.Errorf("job callback must not be nil")
	}

	s.Cancel(name)

	ctx, cancel := context.WithCancel(context.Background())
	timer := time.NewTimer(after)

	s.mu.Lock()
	s.cancels[name] = func() {
		cancel()
		if !timer.Stop() {
			select {
			case <-timer.C:
			default:
			}
		}
	}
	s.mu.Unlock()

	go func() {
		defer s.Cancel(name)
		select {
		case <-ctx.Done():
			return
		case <-timer.C:
			fn(ctx)
		}
	}()

	return func() { s.Cancel(name) }, nil
}

func (s *LocalScheduler) Cancel(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if cancel, ok := s.cancels[name]; ok {
		cancel()
		delete(s.cancels, name)
	}
}
