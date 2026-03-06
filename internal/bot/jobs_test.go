package bot

import (
	"context"
	"testing"
	"time"

	"github.com/vldc-hq/vldc-bot/internal/store"
)

type fakeScheduler struct {
	once      map[string]func(context.Context)
	repeating map[string]func(context.Context)
	canceled  map[string]bool
}

func newFakeScheduler() *fakeScheduler {
	return &fakeScheduler{
		once:      map[string]func(context.Context){},
		repeating: map[string]func(context.Context){},
		canceled:  map[string]bool{},
	}
}

func (f *fakeScheduler) RunRepeating(name string, _ time.Duration, fn func(context.Context)) (CancelFunc, error) {
	f.repeating[name] = fn
	return func() { f.Cancel(name) }, nil
}

func (f *fakeScheduler) RunOnce(name string, _ time.Duration, fn func(context.Context)) (CancelFunc, error) {
	f.once[name] = fn
	return func() { f.Cancel(name) }, nil
}

func (f *fakeScheduler) Cancel(name string) {
	f.canceled[name] = true
	delete(f.once, name)
	delete(f.repeating, name)
}

func TestBuktopuhaRoundScheduling(t *testing.T) {
	s := newFakeScheduler()
	tg := &fakeTG{}
	r := &Runtime{scheduler: s, gw: tg, deps: Dependencies{BuktopuhaGame: NewBuktopuhaState()}}

	_, _ = r.deps.BuktopuhaGame.Start(777)
	r.scheduleBuktopuhaRound(777)

	if s.once[r.bukHint1Job(777)] == nil || s.once[r.bukHint2Job(777)] == nil || s.once[r.bukEndJob(777)] == nil {
		t.Fatalf("expected buktopuha hint/end jobs to be scheduled")
	}
}

func TestBuktopuhaGuessCancelsJobs(t *testing.T) {
	s := newFakeScheduler()
	tg := &fakeTG{}
	r := &Runtime{scheduler: s, gw: tg, deps: Dependencies{BuktopuhaGame: NewBuktopuhaState()}}

	word, _ := r.deps.BuktopuhaGame.Start(777)
	r.scheduleBuktopuhaRound(777)
	r.handlePassiveText(context.Background(), IncomingUpdate{ChatID: 777, UserID: 1, Text: "my guess is " + word})

	if !s.canceled[r.bukHint1Job(777)] || !s.canceled[r.bukHint2Job(777)] || !s.canceled[r.bukEndJob(777)] {
		t.Fatalf("expected buktopuha jobs to be canceled after guess")
	}
}

func TestTowelCleanupSchedulerBansExpired(t *testing.T) {
	s := newFakeScheduler()
	tg := &fakeTG{}
	qr := &fakeQuarantineRepo{users: map[int64]store.QuarantineUser{
		1: {UserID: 1, Until: time.Now().Add(-time.Minute)},
		2: {UserID: 2, Until: time.Now().Add(time.Minute)},
	}}
	modes := NewChatModes()
	modes.SetTowel(123, true)

	r := &Runtime{
		scheduler: s,
		gw:        tg,
		deps: Dependencies{
			Quarantine:  qr,
			Modes:       modes,
			GroupChatID: "123",
		},
	}

	r.startTowelCleanupScheduler()
	job := s.repeating["towel_quarantine_cleanup"]
	if job == nil {
		t.Fatalf("expected cleanup job to be scheduled")
	}

	job(context.Background())

	if len(tg.banned) != 1 || tg.banned[0] != 1 {
		t.Fatalf("expected user 1 to be banned, got=%v", tg.banned)
	}
	if _, ok := qr.users[1]; ok {
		t.Fatalf("expected expired user to be deleted from quarantine")
	}
	if _, ok := qr.users[2]; !ok {
		t.Fatalf("expected non-expired user to stay in quarantine")
	}
}
