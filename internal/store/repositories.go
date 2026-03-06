package store

import (
	"context"
	"time"
)

type TrustedUser struct {
	UserID   int64
	ByUserID int64
	At       time.Time
}

type SinceTopic struct {
	Topic         string
	SinceDateTime time.Time
	Count         int
}

type PrismWord struct {
	Word    string
	Count   int
	LastUse time.Time
}

type RollHussar struct {
	UserID          int64
	MetaJSON        string
	ShotCounter     int
	MissCounter     int
	DeadCounter     int
	TotalTimeInClub int
	FirstShot       time.Time
	LastShot        time.Time
}

type QuarantineUser struct {
	UserID      int64
	RelMessages string
	Until       time.Time
}

type BuktopuhaPlayer struct {
	UserID      int64
	MetaJSON    string
	GameCounter int
	WinCounter  int
	TotalScore  int
	CreatedAt   time.Time
	UpdatedAt   time.Time
}

type PeninsulaUser struct {
	UserID   int64
	MetaJSON string
}

type AOCState struct {
	DataJSON string
}

type TrustedUsersRepository interface {
	Get(ctx context.Context, userID int64) (TrustedUser, bool, error)
	Upsert(ctx context.Context, userID int64, byUserID int64, at time.Time) error
	Delete(ctx context.Context, userID int64) error
	IsTrusted(ctx context.Context, userID int64) (bool, error)
}

type SinceTopicsRepository interface {
	Get(ctx context.Context, topic string) (SinceTopic, bool, error)
	Upsert(ctx context.Context, topic string, since time.Time, count int) error
	ListTop(ctx context.Context, limit int) ([]SinceTopic, error)
}

type PrismWordsRepository interface {
	Increment(ctx context.Context, word string, at time.Time) error
	ListAll(ctx context.Context) ([]PrismWord, error)
}

type RollHussarsRepository interface {
	Get(ctx context.Context, userID int64) (RollHussar, bool, error)
	ListAll(ctx context.Context) ([]RollHussar, error)
	Add(ctx context.Context, userID int64, metaJSON string, at time.Time) error
	MarkDead(ctx context.Context, userID int64, muteMinutes int, at time.Time) error
	MarkMiss(ctx context.Context, userID int64, at time.Time) error
	Delete(ctx context.Context, userID int64) error
	DeleteAll(ctx context.Context) error
}

type QuarantineRepository interface {
	Get(ctx context.Context, userID int64) (QuarantineUser, bool, error)
	ListAll(ctx context.Context) ([]QuarantineUser, error)
	Add(ctx context.Context, userID int64, until time.Time) error
	AddRelatedMessage(ctx context.Context, userID int64, messageID int64) error
	Delete(ctx context.Context, userID int64) error
	DeleteAll(ctx context.Context) error
}

type BuktopuhaRepository interface {
	Get(ctx context.Context, userID int64) (BuktopuhaPlayer, bool, error)
	ListAll(ctx context.Context) ([]BuktopuhaPlayer, error)
	Add(ctx context.Context, userID int64, metaJSON string, score int, at time.Time) error
	IncrementGame(ctx context.Context, userID int64, at time.Time) error
	IncrementWin(ctx context.Context, userID int64, score int, at time.Time) error
	Delete(ctx context.Context, userID int64) error
	DeleteAll(ctx context.Context) error
}

type PeninsulaRepository interface {
	Upsert(ctx context.Context, userID int64, metaJSON string) error
	ListTop(ctx context.Context, limit int) ([]PeninsulaUser, error)
}

type AOCRepository interface {
	Get(ctx context.Context) (AOCState, bool, error)
	Upsert(ctx context.Context, dataJSON string) error
	DeleteAll(ctx context.Context) error
}
