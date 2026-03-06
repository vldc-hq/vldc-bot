package bot

import (
	"context"
	"sync/atomic"
	"testing"
	"time"
)

func TestLocalSchedulerRunOnce(t *testing.T) {
	s := NewLocalScheduler()

	var called atomic.Int32
	done := make(chan struct{})

	_, err := s.RunOnce("once", 10*time.Millisecond, func(context.Context) {
		called.Add(1)
		close(done)
	})
	if err != nil {
		t.Fatalf("run once: %v", err)
	}

	select {
	case <-done:
	case <-time.After(time.Second):
		t.Fatalf("timeout waiting for scheduled callback")
	}

	if called.Load() != 1 {
		t.Fatalf("unexpected callback count: got=%d want=%d", called.Load(), 1)
	}
}

func TestLocalSchedulerCancelRepeating(t *testing.T) {
	s := NewLocalScheduler()

	var called atomic.Int32
	cancel, err := s.RunRepeating("repeat", 10*time.Millisecond, func(context.Context) {
		called.Add(1)
	})
	if err != nil {
		t.Fatalf("run repeating: %v", err)
	}

	time.Sleep(40 * time.Millisecond)
	cancel()

	valueAtCancel := called.Load()
	time.Sleep(40 * time.Millisecond)

	after := called.Load()
	if after > valueAtCancel+1 {
		t.Fatalf("callback should stop shortly after cancel: before=%d after=%d", valueAtCancel, after)
	}
}
