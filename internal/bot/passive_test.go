package bot

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/vldc-hq/vldc-bot/internal/store"
)

type fakeQuarantineRepo struct {
	users map[int64]store.QuarantineUser
}

type fakeBioChecker struct{ ok bool }

func (f fakeBioChecker) IsWorthyBio(string) bool { return f.ok }

type fakeSpeech struct{ out string }

func (f fakeSpeech) Recognize(context.Context, string) (string, error) { return f.out, nil }

type fakeTranslator struct{ out string }

func (f fakeTranslator) Translate(context.Context, string, string, string) (string, error) {
	return f.out, nil
}

func (r *fakeQuarantineRepo) Get(_ context.Context, userID int64) (store.QuarantineUser, bool, error) {
	v, ok := r.users[userID]
	return v, ok, nil
}

func (r *fakeQuarantineRepo) ListAll(context.Context) ([]store.QuarantineUser, error) {
	out := make([]store.QuarantineUser, 0, len(r.users))
	for _, v := range r.users {
		out = append(out, v)
	}
	return out, nil
}

func (r *fakeQuarantineRepo) Add(_ context.Context, userID int64, until time.Time) error {
	if r.users == nil {
		r.users = map[int64]store.QuarantineUser{}
	}
	r.users[userID] = store.QuarantineUser{UserID: userID, RelMessages: "[]", Until: until}
	return nil
}

func (r *fakeQuarantineRepo) AddRelatedMessage(_ context.Context, userID int64, messageID int64) error {
	if r.users == nil {
		r.users = map[int64]store.QuarantineUser{}
	}
	v := r.users[userID]
	var ids []int64
	if v.RelMessages != "" {
		_ = json.Unmarshal([]byte(v.RelMessages), &ids)
	}
	ids = append(ids, messageID)
	data, _ := json.Marshal(ids)
	v.RelMessages = string(data)
	r.users[userID] = v
	return nil
}

func (r *fakeQuarantineRepo) Delete(_ context.Context, userID int64) error {
	delete(r.users, userID)
	return nil
}

func (r *fakeQuarantineRepo) DeleteAll(context.Context) error {
	r.users = map[int64]store.QuarantineUser{}
	return nil
}

func TestFoolsTransform(t *testing.T) {
	if got := foolsTransform("мама мыла раму"); got == "мама мыла раму" {
		t.Fatalf("expected transformed text, got=%q", got)
	}
}

func TestAllowedReplyTo(t *testing.T) {
	if !allowedReplyTo("[]", 10) {
		t.Fatalf("expected empty list to allow any reply id")
	}
	if !allowedReplyTo("[10,20]", 10) {
		t.Fatalf("expected exact reply id to be allowed")
	}
	if allowedReplyTo("[10,20]", 99) {
		t.Fatalf("expected unknown reply id to be denied")
	}
}

func TestTowelModeQuarantineFlow(t *testing.T) {
	r := &Runtime{
		deps: Dependencies{Modes: NewChatModes(), Quarantine: &fakeQuarantineRepo{users: map[int64]store.QuarantineUser{}}, BioChecker: fakeBioChecker{ok: true}},
		gw:   &fakeTG{},
	}

	r.handleTowelMode(context.Background(), IncomingUpdate{ChatID: 1, NewMembers: []int64{101}})

	qr := r.deps.Quarantine.(*fakeQuarantineRepo)
	item, ok := qr.users[101]
	if !ok {
		t.Fatalf("expected new member in quarantine")
	}

	var ids []int64
	if err := json.Unmarshal([]byte(item.RelMessages), &ids); err != nil || len(ids) == 0 {
		t.Fatalf("expected related message id to be recorded, err=%v ids=%v", err, ids)
	}

	r.handleTowelMode(context.Background(), IncomingUpdate{ChatID: 1, UserID: 101, ReplyToMsgID: int(ids[0]), Text: "hello i am software engineer"})
	if _, still := qr.users[101]; still {
		t.Fatalf("expected user to leave quarantine after valid reply")
	}
}

func TestTowelModeRejectsSpamBio(t *testing.T) {
	r := &Runtime{
		deps: Dependencies{Modes: NewChatModes(), Quarantine: &fakeQuarantineRepo{users: map[int64]store.QuarantineUser{}}, BioChecker: fakeBioChecker{ok: false}},
		gw:   &fakeTG{},
	}

	r.handleTowelMode(context.Background(), IncomingUpdate{ChatID: 1, NewMembers: []int64{101}})
	qr := r.deps.Quarantine.(*fakeQuarantineRepo)
	item := qr.users[101]

	var ids []int64
	_ = json.Unmarshal([]byte(item.RelMessages), &ids)
	r.handleTowelMode(context.Background(), IncomingUpdate{ChatID: 1, UserID: 101, ReplyToMsgID: int(ids[0]), MessageID: 500, Text: "i am investor and looking for partners"})

	if _, still := qr.users[101]; !still {
		t.Fatalf("expected user to remain in quarantine after spam reply")
	}
	tg := r.gw.(*fakeTG)
	if len(tg.deleted) == 0 || tg.deleted[len(tg.deleted)-1] != 500 {
		t.Fatalf("expected spam intro message to be deleted, got=%v", tg.deleted)
	}
}

func TestNastyaModeSpeechAppend(t *testing.T) {
	tg := &fakeTG{}
	r := &Runtime{deps: Dependencies{Modes: NewChatModes(), Speech: fakeSpeech{out: "hello"}}, gw: tg}
	r.deps.Modes.SetNastya(1, true)

	r.handleNastyaMode(context.Background(), IncomingUpdate{ChatID: 1, UserID: 7, Username: "u", HasVoice: true, MessageID: 99})

	if len(tg.messages) == 0 || tg.messages[len(tg.messages)-1] == "" {
		t.Fatalf("expected nastya mode message")
	}
	if tg.messages[len(tg.messages)-1] != "@u voice/video is disabled in this chat\nrecognized: hello" {
		t.Fatalf("unexpected nastya message: %q", tg.messages[len(tg.messages)-1])
	}
}

func TestFoolsModeUsesTranslator(t *testing.T) {
	tg := &fakeTG{}
	r := &Runtime{deps: Dependencies{Modes: NewChatModes(), Translator: fakeTranslator{out: "translated"}}, gw: tg}
	r.deps.Modes.SetFools(1, true)

	r.handleFoolsMode(context.Background(), IncomingUpdate{ChatID: 1, UserID: 7, Username: "u", Text: "оригинал", MessageID: 11})

	if len(tg.messages) == 0 || tg.messages[len(tg.messages)-1] != "@u: translated" {
		t.Fatalf("unexpected fools output: %v", tg.messages)
	}
}
