package sqlite

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/vldc-hq/vldc-bot/internal/store"
)

type (
	TrustedUsersRepo struct{ db *sql.DB }
	SinceTopicsRepo  struct{ db *sql.DB }
	PrismWordsRepo   struct{ db *sql.DB }
	RollHussarsRepo  struct{ db *sql.DB }
	QuarantineRepo   struct{ db *sql.DB }
	BuktopuhaRepo    struct{ db *sql.DB }
	PeninsulaRepo    struct{ db *sql.DB }
	AOCRepo          struct{ db *sql.DB }
)

func NewTrustedUsersRepo(db *sql.DB) *TrustedUsersRepo { return &TrustedUsersRepo{db: db} }
func NewSinceTopicsRepo(db *sql.DB) *SinceTopicsRepo   { return &SinceTopicsRepo{db: db} }
func NewPrismWordsRepo(db *sql.DB) *PrismWordsRepo     { return &PrismWordsRepo{db: db} }
func NewRollHussarsRepo(db *sql.DB) *RollHussarsRepo   { return &RollHussarsRepo{db: db} }
func NewQuarantineRepo(db *sql.DB) *QuarantineRepo     { return &QuarantineRepo{db: db} }
func NewBuktopuhaRepo(db *sql.DB) *BuktopuhaRepo       { return &BuktopuhaRepo{db: db} }
func NewPeninsulaRepo(db *sql.DB) *PeninsulaRepo       { return &PeninsulaRepo{db: db} }
func NewAOCRepo(db *sql.DB) *AOCRepo                   { return &AOCRepo{db: db} }

func (r *TrustedUsersRepo) Get(ctx context.Context, userID int64) (store.TrustedUser, bool, error) {
	row := r.db.QueryRowContext(ctx, `SELECT user_id, "by", datetime FROM trusted_users WHERE user_id = ?`, userID)
	var out store.TrustedUser
	if err := row.Scan(&out.UserID, &out.ByUserID, &out.At); err != nil {
		if err == sql.ErrNoRows {
			return store.TrustedUser{}, false, nil
		}
		return store.TrustedUser{}, false, fmt.Errorf("get trusted user: %w", err)
	}
	return out, true, nil
}

func (r *TrustedUsersRepo) Upsert(ctx context.Context, userID int64, byUserID int64, at time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `INSERT OR REPLACE INTO trusted_users (user_id, "by", datetime) VALUES (?, ?, ?)`, userID, byUserID, at)
		if err != nil {
			return fmt.Errorf("upsert trusted user: %w", err)
		}
		return nil
	})
}

func (r *TrustedUsersRepo) Delete(ctx context.Context, userID int64) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM trusted_users WHERE user_id = ?`, userID)
		if err != nil {
			return fmt.Errorf("delete trusted user: %w", err)
		}
		return nil
	})
}

func (r *TrustedUsersRepo) IsTrusted(ctx context.Context, userID int64) (bool, error) {
	row := r.db.QueryRowContext(ctx, `SELECT 1 FROM trusted_users WHERE user_id = ?`, userID)
	var x int
	err := row.Scan(&x)
	if err == sql.ErrNoRows {
		return false, nil
	}
	if err != nil {
		return false, fmt.Errorf("is trusted: %w", err)
	}
	return true, nil
}

func (r *SinceTopicsRepo) Get(ctx context.Context, topic string) (store.SinceTopic, bool, error) {
	t := strings.ToLower(topic)
	row := r.db.QueryRowContext(ctx, `SELECT topic, since_datetime, count FROM since_topics WHERE topic = ?`, t)
	var out store.SinceTopic
	if err := row.Scan(&out.Topic, &out.SinceDateTime, &out.Count); err != nil {
		if err == sql.ErrNoRows {
			return store.SinceTopic{}, false, nil
		}
		return store.SinceTopic{}, false, fmt.Errorf("get since topic: %w", err)
	}
	return out, true, nil
}

func (r *SinceTopicsRepo) Upsert(ctx context.Context, topic string, since time.Time, count int) error {
	t := strings.ToLower(topic)
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		res, err := tx.ExecContext(ctx, `UPDATE since_topics SET count = count + 1, since_datetime = ? WHERE topic = ?`, time.Now(), t)
		if err != nil {
			return fmt.Errorf("update since topic: %w", err)
		}
		affected, err := res.RowsAffected()
		if err != nil {
			return fmt.Errorf("since topic rows affected: %w", err)
		}
		if affected == 0 {
			_, err = tx.ExecContext(ctx, `INSERT INTO since_topics (topic, since_datetime, count) VALUES (?, ?, ?)`, t, since, count)
			if err != nil {
				return fmt.Errorf("insert since topic: %w", err)
			}
		}
		return nil
	})
}

func (r *SinceTopicsRepo) ListTop(ctx context.Context, limit int) ([]store.SinceTopic, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT topic, since_datetime, count FROM since_topics ORDER BY count DESC LIMIT ?`, limit)
	if err != nil {
		return nil, fmt.Errorf("list since topics: %w", err)
	}
	defer rows.Close()

	out := make([]store.SinceTopic, 0)
	for rows.Next() {
		var item store.SinceTopic
		if err := rows.Scan(&item.Topic, &item.SinceDateTime, &item.Count); err != nil {
			return nil, fmt.Errorf("scan since topic: %w", err)
		}
		out = append(out, item)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate since topics: %w", err)
	}

	return out, nil
}

func (r *PrismWordsRepo) Increment(ctx context.Context, word string, at time.Time) error {
	w := strings.ToLower(word)
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		res, err := tx.ExecContext(ctx, `UPDATE prism_words SET count = count + 1, last_use = ? WHERE word = ?`, at, w)
		if err != nil {
			return fmt.Errorf("update prism word: %w", err)
		}
		affected, err := res.RowsAffected()
		if err != nil {
			return fmt.Errorf("prism word rows affected: %w", err)
		}
		if affected == 0 {
			_, err = tx.ExecContext(ctx, `INSERT INTO prism_words (word, count, last_use) VALUES (?, 1, ?)`, w, at)
			if err != nil {
				return fmt.Errorf("insert prism word: %w", err)
			}
		}
		return nil
	})
}

func (r *PrismWordsRepo) ListAll(ctx context.Context) ([]store.PrismWord, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT word, count, last_use FROM prism_words ORDER BY count DESC`)
	if err != nil {
		return nil, fmt.Errorf("list prism words: %w", err)
	}
	defer rows.Close()

	out := make([]store.PrismWord, 0)
	for rows.Next() {
		var item store.PrismWord
		if err := rows.Scan(&item.Word, &item.Count, &item.LastUse); err != nil {
			return nil, fmt.Errorf("scan prism word: %w", err)
		}
		out = append(out, item)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate prism words: %w", err)
	}

	return out, nil
}

func (r *RollHussarsRepo) Get(ctx context.Context, userID int64) (store.RollHussar, bool, error) {
	row := r.db.QueryRowContext(ctx, `SELECT user_id, meta, shot_counter, miss_counter, dead_counter, total_time_in_club, first_shot, last_shot FROM roll_hussars WHERE user_id = ?`, userID)
	var item store.RollHussar
	if err := row.Scan(&item.UserID, &item.MetaJSON, &item.ShotCounter, &item.MissCounter, &item.DeadCounter, &item.TotalTimeInClub, &item.FirstShot, &item.LastShot); err != nil {
		if err == sql.ErrNoRows {
			return store.RollHussar{}, false, nil
		}
		return store.RollHussar{}, false, fmt.Errorf("get roll hussar: %w", err)
	}
	return item, true, nil
}

func (r *RollHussarsRepo) ListAll(ctx context.Context) ([]store.RollHussar, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT user_id, meta, shot_counter, miss_counter, dead_counter, total_time_in_club, first_shot, last_shot FROM roll_hussars ORDER BY total_time_in_club DESC`)
	if err != nil {
		return nil, fmt.Errorf("list roll hussars: %w", err)
	}
	defer rows.Close()

	out := make([]store.RollHussar, 0)
	for rows.Next() {
		var item store.RollHussar
		if err := rows.Scan(&item.UserID, &item.MetaJSON, &item.ShotCounter, &item.MissCounter, &item.DeadCounter, &item.TotalTimeInClub, &item.FirstShot, &item.LastShot); err != nil {
			return nil, fmt.Errorf("scan roll hussar: %w", err)
		}
		out = append(out, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate roll hussars: %w", err)
	}
	return out, nil
}

func (r *RollHussarsRepo) Add(ctx context.Context, userID int64, metaJSON string, at time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `INSERT INTO roll_hussars (user_id, meta, shot_counter, miss_counter, dead_counter, total_time_in_club, first_shot, last_shot) VALUES (?, ?, 0, 0, 0, 0, ?, ?)`, userID, metaJSON, at, at)
		if err != nil {
			return fmt.Errorf("add roll hussar: %w", err)
		}
		return nil
	})
}

func (r *RollHussarsRepo) MarkDead(ctx context.Context, userID int64, muteMinutes int, at time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `UPDATE roll_hussars SET shot_counter = shot_counter + 1, dead_counter = dead_counter + 1, total_time_in_club = total_time_in_club + ?, last_shot = ? WHERE user_id = ?`, muteMinutes*60, at, userID)
		if err != nil {
			return fmt.Errorf("mark roll hussar dead: %w", err)
		}
		return nil
	})
}

func (r *RollHussarsRepo) MarkMiss(ctx context.Context, userID int64, at time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `UPDATE roll_hussars SET shot_counter = shot_counter + 1, miss_counter = miss_counter + 1, last_shot = ? WHERE user_id = ?`, at, userID)
		if err != nil {
			return fmt.Errorf("mark roll hussar miss: %w", err)
		}
		return nil
	})
}

func (r *RollHussarsRepo) Delete(ctx context.Context, userID int64) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM roll_hussars WHERE user_id = ?`, userID)
		if err != nil {
			return fmt.Errorf("delete roll hussar: %w", err)
		}
		return nil
	})
}

func (r *RollHussarsRepo) DeleteAll(ctx context.Context) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM roll_hussars`)
		if err != nil {
			return fmt.Errorf("delete all roll hussars: %w", err)
		}
		return nil
	})
}

func (r *QuarantineRepo) Get(ctx context.Context, userID int64) (store.QuarantineUser, bool, error) {
	row := r.db.QueryRowContext(ctx, `SELECT user_id, rel_messages, datetime FROM towel_quarantine WHERE user_id = ?`, userID)
	var item store.QuarantineUser
	if err := row.Scan(&item.UserID, &item.RelMessages, &item.Until); err != nil {
		if err == sql.ErrNoRows {
			return store.QuarantineUser{}, false, nil
		}
		return store.QuarantineUser{}, false, fmt.Errorf("get quarantine user: %w", err)
	}
	return item, true, nil
}

func (r *QuarantineRepo) ListAll(ctx context.Context) ([]store.QuarantineUser, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT user_id, rel_messages, datetime FROM towel_quarantine`)
	if err != nil {
		return nil, fmt.Errorf("list quarantine users: %w", err)
	}
	defer rows.Close()

	out := make([]store.QuarantineUser, 0)
	for rows.Next() {
		var item store.QuarantineUser
		if err := rows.Scan(&item.UserID, &item.RelMessages, &item.Until); err != nil {
			return nil, fmt.Errorf("scan quarantine user: %w", err)
		}
		out = append(out, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate quarantine users: %w", err)
	}
	return out, nil
}

func (r *QuarantineRepo) Add(ctx context.Context, userID int64, until time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `INSERT OR IGNORE INTO towel_quarantine (user_id, rel_messages, datetime) VALUES (?, ?, ?)`, userID, "[]", until)
		if err != nil {
			return fmt.Errorf("add quarantine user: %w", err)
		}
		return nil
	})
}

func (r *QuarantineRepo) AddRelatedMessage(ctx context.Context, userID int64, messageID int64) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		var raw string
		err := tx.QueryRowContext(ctx, `SELECT rel_messages FROM towel_quarantine WHERE user_id = ?`, userID).Scan(&raw)
		if err != nil {
			if err == sql.ErrNoRows {
				return nil
			}
			return fmt.Errorf("load quarantine rel messages: %w", err)
		}

		var existing []int64
		if err := json.Unmarshal([]byte(raw), &existing); err != nil {
			return fmt.Errorf("unmarshal quarantine rel messages: %w", err)
		}

		seen := make(map[int64]struct{}, len(existing)+1)
		for _, x := range existing {
			seen[x] = struct{}{}
		}
		seen[messageID] = struct{}{}

		merged := make([]int64, 0, len(seen))
		for x := range seen {
			merged = append(merged, x)
		}
		encoded, err := json.Marshal(merged)
		if err != nil {
			return fmt.Errorf("marshal quarantine rel messages: %w", err)
		}

		_, err = tx.ExecContext(ctx, `UPDATE towel_quarantine SET rel_messages = ? WHERE user_id = ?`, string(encoded), userID)
		if err != nil {
			return fmt.Errorf("update quarantine rel messages: %w", err)
		}

		return nil
	})
}

func (r *QuarantineRepo) Delete(ctx context.Context, userID int64) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM towel_quarantine WHERE user_id = ?`, userID)
		if err != nil {
			return fmt.Errorf("delete quarantine user: %w", err)
		}
		return nil
	})
}

func (r *QuarantineRepo) DeleteAll(ctx context.Context) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM towel_quarantine`)
		if err != nil {
			return fmt.Errorf("delete all quarantine users: %w", err)
		}
		return nil
	})
}

func (r *BuktopuhaRepo) Get(ctx context.Context, userID int64) (store.BuktopuhaPlayer, bool, error) {
	row := r.db.QueryRowContext(ctx, `SELECT user_id, meta, game_counter, win_counter, total_score, created_at, updated_at FROM buktopuha_players WHERE user_id = ?`, userID)
	var item store.BuktopuhaPlayer
	if err := row.Scan(&item.UserID, &item.MetaJSON, &item.GameCounter, &item.WinCounter, &item.TotalScore, &item.CreatedAt, &item.UpdatedAt); err != nil {
		if err == sql.ErrNoRows {
			return store.BuktopuhaPlayer{}, false, nil
		}
		return store.BuktopuhaPlayer{}, false, fmt.Errorf("get buktopuha player: %w", err)
	}
	return item, true, nil
}

func (r *BuktopuhaRepo) ListAll(ctx context.Context) ([]store.BuktopuhaPlayer, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT user_id, meta, game_counter, win_counter, total_score, created_at, updated_at FROM buktopuha_players ORDER BY win_counter DESC`)
	if err != nil {
		return nil, fmt.Errorf("list buktopuha players: %w", err)
	}
	defer rows.Close()

	out := make([]store.BuktopuhaPlayer, 0)
	for rows.Next() {
		var item store.BuktopuhaPlayer
		if err := rows.Scan(&item.UserID, &item.MetaJSON, &item.GameCounter, &item.WinCounter, &item.TotalScore, &item.CreatedAt, &item.UpdatedAt); err != nil {
			return nil, fmt.Errorf("scan buktopuha player: %w", err)
		}
		out = append(out, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate buktopuha players: %w", err)
	}
	return out, nil
}

func (r *BuktopuhaRepo) Add(ctx context.Context, userID int64, metaJSON string, score int, at time.Time) error {
	gameInc := 0
	winInc := 0
	if score == 0 {
		gameInc = 1
	}
	if score > 0 {
		winInc = 1
	}

	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `INSERT INTO buktopuha_players (user_id, meta, game_counter, win_counter, total_score, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)`, userID, metaJSON, gameInc, winInc, score, at, at)
		if err != nil {
			return fmt.Errorf("add buktopuha player: %w", err)
		}
		return nil
	})
}

func (r *BuktopuhaRepo) IncrementGame(ctx context.Context, userID int64, at time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `UPDATE buktopuha_players SET game_counter = game_counter + 1, updated_at = ? WHERE user_id = ?`, at, userID)
		if err != nil {
			return fmt.Errorf("increment buktopuha game: %w", err)
		}
		return nil
	})
}

func (r *BuktopuhaRepo) IncrementWin(ctx context.Context, userID int64, score int, at time.Time) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `UPDATE buktopuha_players SET win_counter = win_counter + 1, total_score = total_score + ?, updated_at = ? WHERE user_id = ?`, score, at, userID)
		if err != nil {
			return fmt.Errorf("increment buktopuha win: %w", err)
		}
		return nil
	})
}

func (r *BuktopuhaRepo) Delete(ctx context.Context, userID int64) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM buktopuha_players WHERE user_id = ?`, userID)
		if err != nil {
			return fmt.Errorf("delete buktopuha player: %w", err)
		}
		return nil
	})
}

func (r *BuktopuhaRepo) DeleteAll(ctx context.Context) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM buktopuha_players`)
		if err != nil {
			return fmt.Errorf("delete all buktopuha players: %w", err)
		}
		return nil
	})
}

func (r *PeninsulaRepo) Upsert(ctx context.Context, userID int64, metaJSON string) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `INSERT OR REPLACE INTO peninsula_users (user_id, meta) VALUES (?, ?)`, userID, metaJSON)
		if err != nil {
			return fmt.Errorf("upsert peninsula user: %w", err)
		}
		return nil
	})
}

func (r *PeninsulaRepo) ListTop(ctx context.Context, limit int) ([]store.PeninsulaUser, error) {
	rows, err := r.db.QueryContext(ctx, `SELECT user_id, meta FROM peninsula_users ORDER BY user_id ASC LIMIT ?`, limit)
	if err != nil {
		return nil, fmt.Errorf("list peninsula users: %w", err)
	}
	defer rows.Close()

	out := make([]store.PeninsulaUser, 0)
	for rows.Next() {
		var item store.PeninsulaUser
		if err := rows.Scan(&item.UserID, &item.MetaJSON); err != nil {
			return nil, fmt.Errorf("scan peninsula user: %w", err)
		}
		out = append(out, item)
	}
	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("iterate peninsula users: %w", err)
	}
	return out, nil
}

func (r *AOCRepo) Get(ctx context.Context) (store.AOCState, bool, error) {
	row := r.db.QueryRowContext(ctx, `SELECT data FROM aoc WHERE id = 0`)
	var data string
	if err := row.Scan(&data); err != nil {
		if err == sql.ErrNoRows {
			return store.AOCState{}, false, nil
		}
		return store.AOCState{}, false, fmt.Errorf("get aoc state: %w", err)
	}

	return store.AOCState{DataJSON: data}, true, nil
}

func (r *AOCRepo) Upsert(ctx context.Context, dataJSON string) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `INSERT OR REPLACE INTO aoc (id, data) VALUES (0, ?)`, dataJSON)
		if err != nil {
			return fmt.Errorf("upsert aoc state: %w", err)
		}
		return nil
	})
}

func (r *AOCRepo) DeleteAll(ctx context.Context) error {
	return withTx(ctx, r.db, func(tx *sql.Tx) error {
		_, err := tx.ExecContext(ctx, `DELETE FROM aoc`)
		if err != nil {
			return fmt.Errorf("delete all aoc state: %w", err)
		}
		return nil
	})
}

var (
	_ store.TrustedUsersRepository = (*TrustedUsersRepo)(nil)
	_ store.SinceTopicsRepository  = (*SinceTopicsRepo)(nil)
	_ store.PrismWordsRepository   = (*PrismWordsRepo)(nil)
	_ store.RollHussarsRepository  = (*RollHussarsRepo)(nil)
	_ store.QuarantineRepository   = (*QuarantineRepo)(nil)
	_ store.BuktopuhaRepository    = (*BuktopuhaRepo)(nil)
	_ store.PeninsulaRepository    = (*PeninsulaRepo)(nil)
	_ store.AOCRepository          = (*AOCRepo)(nil)
)
