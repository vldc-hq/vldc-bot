package db

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/jmoiron/sqlx"
	_ "modernc.org/sqlite" // SQLite driver
)

type DB struct {
	db *sqlx.DB
}

func New(dbPath string) (*DB, error) {
	conn, err := sqlx.Open("sqlite", dbPath+"?_pragma=journal_mode(WAL)&_pragma=busy_timeout(5000)")
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}

	// SQLite: single writer, multiple readers
	conn.SetMaxOpenConns(1)

	d := &DB{db: conn}
	if err := d.init(); err != nil {
		return nil, fmt.Errorf("init db: %w", err)
	}
	return d, nil
}

func (d *DB) Close() error {
	return d.db.Close()
}

func (d *DB) init() error {
	schema := `
	CREATE TABLE IF NOT EXISTS trusted_users (
		user_id INTEGER PRIMARY KEY,
		added_by INTEGER,
		created_at TEXT
	);
	CREATE TABLE IF NOT EXISTS buktopuha_players (
		user_id INTEGER PRIMARY KEY,
		meta TEXT,
		game_counter INTEGER DEFAULT 0,
		win_counter INTEGER DEFAULT 0,
		total_score INTEGER DEFAULT 0,
		created_at TEXT,
		updated_at TEXT
	);
	CREATE TABLE IF NOT EXISTS towel_quarantine (
		user_id INTEGER PRIMARY KEY,
		rel_messages TEXT,
		expires_at TEXT
	);
	CREATE TABLE IF NOT EXISTS since_topics (
		topic TEXT PRIMARY KEY,
		since_datetime TEXT,
		count INTEGER DEFAULT 0
	);
	CREATE TABLE IF NOT EXISTS roll_hussars (
		user_id INTEGER PRIMARY KEY,
		meta TEXT,
		shot_counter INTEGER DEFAULT 0,
		miss_counter INTEGER DEFAULT 0,
		dead_counter INTEGER DEFAULT 0,
		total_time_in_club INTEGER DEFAULT 0,
		first_shot TEXT,
		last_shot TEXT
	);
	CREATE TABLE IF NOT EXISTS prism_words (
		word TEXT PRIMARY KEY,
		count INTEGER DEFAULT 0,
		last_use TEXT
	);
	CREATE TABLE IF NOT EXISTS peninsula_users (
		user_id INTEGER PRIMARY KEY,
		meta TEXT
	);
	CREATE TABLE IF NOT EXISTS aoc (
		id INTEGER PRIMARY KEY CHECK (id = 0),
		data TEXT
	);
	CREATE TABLE IF NOT EXISTS length_users (
		user_id INTEGER PRIMARY KEY,
		username TEXT,
		first_name TEXT,
		last_name TEXT,
		length INTEGER DEFAULT 0
	);`
	_, err := d.db.Exec(schema)
	return err
}

// --- Trusted Users ---

type TrustedUser struct {
	UserID    int64  `db:"user_id"`
	AddedBy   int64  `db:"added_by"`
	CreatedAt string `db:"created_at"`
}

func (d *DB) TrustUser(userID, adminID int64) error {
	_, err := d.db.Exec(
		`INSERT OR REPLACE INTO trusted_users (user_id, added_by, created_at) VALUES (?, ?, ?)`,
		userID, adminID, time.Now().Format(time.RFC3339),
	)
	return err
}

func (d *DB) UntrustUser(userID int64) error {
	_, err := d.db.Exec(`DELETE FROM trusted_users WHERE user_id = ?`, userID)
	return err
}

func (d *DB) IsUserTrusted(userID int64) (bool, error) {
	var count int
	err := d.db.Get(&count, `SELECT COUNT(1) FROM trusted_users WHERE user_id = ?`, userID)
	return count > 0, err
}

// --- Towel Quarantine ---

type QuarantineUser struct {
	UserID      int64  `db:"user_id"`
	RelMessages string `db:"rel_messages"` // JSON array of message IDs
	ExpiresAt   string `db:"expires_at"`
}

func (q *QuarantineUser) IsExpired() bool {
	t, err := time.Parse(time.RFC3339, q.ExpiresAt)
	if err != nil {
		return true
	}
	return time.Now().After(t)
}

func (q *QuarantineUser) MessageIDs() []int {
	var ids []int
	_ = json.Unmarshal([]byte(q.RelMessages), &ids)
	return ids
}

func (d *DB) AddQuarantineUser(userID int64, quarantineMinutes int) error {
	existing, _ := d.FindQuarantineUser(userID)
	if existing != nil {
		return nil
	}
	expiresAt := time.Now().Add(time.Duration(quarantineMinutes) * time.Minute).Format(time.RFC3339)
	_, err := d.db.Exec(
		`INSERT INTO towel_quarantine (user_id, rel_messages, expires_at) VALUES (?, ?, ?)`,
		userID, "[]", expiresAt,
	)
	return err
}

func (d *DB) FindQuarantineUser(userID int64) (*QuarantineUser, error) {
	var u QuarantineUser
	err := d.db.Get(&u, `SELECT * FROM towel_quarantine WHERE user_id = ?`, userID)
	if err != nil {
		return nil, err
	}
	return &u, nil
}

func (d *DB) FindAllQuarantineUsers() ([]QuarantineUser, error) {
	var users []QuarantineUser
	err := d.db.Select(&users, `SELECT * FROM towel_quarantine`)
	return users, err
}

func (d *DB) AddQuarantineRelMessage(userID int64, messageID int) error {
	u, err := d.FindQuarantineUser(userID)
	if err != nil {
		return err
	}
	ids := u.MessageIDs()
	// deduplicate
	for _, id := range ids {
		if id == messageID {
			return nil
		}
	}
	ids = append(ids, messageID)
	data, _ := json.Marshal(ids)
	_, err = d.db.Exec(`UPDATE towel_quarantine SET rel_messages = ? WHERE user_id = ?`, string(data), userID)
	return err
}

func (d *DB) DeleteQuarantineUser(userID int64) error {
	_, err := d.db.Exec(`DELETE FROM towel_quarantine WHERE user_id = ?`, userID)
	return err
}

func (d *DB) DeleteAllQuarantineUsers() error {
	_, err := d.db.Exec(`DELETE FROM towel_quarantine`)
	return err
}

// --- Roll Hussars ---

type Hussar struct {
	UserID          int64  `db:"user_id"`
	Meta            string `db:"meta"` // JSON
	ShotCounter     int    `db:"shot_counter"`
	MissCounter     int    `db:"miss_counter"`
	DeadCounter     int    `db:"dead_counter"`
	TotalTimeInClub int    `db:"total_time_in_club"` // seconds
	FirstShot       string `db:"first_shot"`
	LastShot        string `db:"last_shot"`
}

func (h *Hussar) Username() string {
	var meta map[string]any
	_ = json.Unmarshal([]byte(h.Meta), &meta)
	if username, ok := meta["username"].(string); ok && username != "" {
		return username
	}
	firstName, _ := meta["first_name"].(string)
	lastName, _ := meta["last_name"].(string)
	name := firstName
	if lastName != "" {
		if name != "" {
			name += " "
		}
		name += lastName
	}
	if name == "" {
		return "unknown"
	}
	return name
}

func (d *DB) GetAllHussars() ([]Hussar, error) {
	var hussars []Hussar
	err := d.db.Select(&hussars, `SELECT * FROM roll_hussars ORDER BY total_time_in_club DESC`)
	return hussars, err
}

func (d *DB) FindHussar(userID int64) (*Hussar, error) {
	var h Hussar
	err := d.db.Get(&h, `SELECT * FROM roll_hussars WHERE user_id = ?`, userID)
	if err != nil {
		return nil, err
	}
	return &h, nil
}

func (d *DB) AddHussar(userID int64, meta string) error {
	now := time.Now().Format(time.RFC3339)
	_, err := d.db.Exec(
		`INSERT INTO roll_hussars (user_id, meta, shot_counter, miss_counter, dead_counter, total_time_in_club, first_shot, last_shot) VALUES (?, ?, 0, 0, 0, 0, ?, ?)`,
		userID, meta, now, now,
	)
	return err
}

func (d *DB) HussarDead(userID int64, muteMinutes int) error {
	_, err := d.db.Exec(
		`UPDATE roll_hussars SET shot_counter = shot_counter + 1, dead_counter = dead_counter + 1, total_time_in_club = total_time_in_club + ?, last_shot = ? WHERE user_id = ?`,
		muteMinutes*60, time.Now().Format(time.RFC3339), userID,
	)
	return err
}

func (d *DB) HussarMiss(userID int64) error {
	_, err := d.db.Exec(
		`UPDATE roll_hussars SET shot_counter = shot_counter + 1, miss_counter = miss_counter + 1, last_shot = ? WHERE user_id = ?`,
		time.Now().Format(time.RFC3339), userID,
	)
	return err
}

func (d *DB) RemoveHussar(userID int64) error {
	_, err := d.db.Exec(`DELETE FROM roll_hussars WHERE user_id = ?`, userID)
	return err
}

func (d *DB) RemoveAllHussars() error {
	_, err := d.db.Exec(`DELETE FROM roll_hussars`)
	return err
}

// --- Since Topics ---

type SinceTopic struct {
	Topic         string `db:"topic"`
	SinceDatetime string `db:"since_datetime"`
	Count         int    `db:"count"`
}

func (d *DB) GetSinceTopic(topic string) (*SinceTopic, error) {
	var t SinceTopic
	err := d.db.Get(&t, `SELECT * FROM since_topics WHERE topic = ?`, topic)
	if err != nil {
		return nil, err
	}
	return &t, nil
}

func (d *DB) UpsertSinceTopic(topic string) error {
	now := time.Now().Format(time.RFC3339)
	_, err := d.db.Exec(
		`INSERT INTO since_topics (topic, since_datetime, count) VALUES (?, ?, 1) ON CONFLICT(topic) DO UPDATE SET count = count + 1, since_datetime = ?`,
		topic, now, now,
	)
	return err
}

func (d *DB) GetAllSinceTopics(limit int) ([]SinceTopic, error) {
	var topics []SinceTopic
	err := d.db.Select(&topics, `SELECT * FROM since_topics ORDER BY count DESC LIMIT ?`, limit)
	return topics, err
}

// --- Prism Words ---

func (d *DB) AddPrismWord(word string) error {
	now := time.Now().Format(time.RFC3339)
	_, err := d.db.Exec(
		`INSERT INTO prism_words (word, count, last_use) VALUES (?, 1, ?) ON CONFLICT(word) DO UPDATE SET count = count + 1, last_use = ?`,
		word, now, now,
	)
	return err
}

type PrismWord struct {
	Word    string `db:"word"`
	Count   int    `db:"count"`
	LastUse string `db:"last_use"`
}

func (d *DB) GetAllPrismWords() ([]PrismWord, error) {
	var words []PrismWord
	err := d.db.Select(&words, `SELECT * FROM prism_words ORDER BY count DESC`)
	return words, err
}

// --- Length Users ---

type LengthUser struct {
	UserID    int64  `db:"user_id"`
	Username  string `db:"username"`
	FirstName string `db:"first_name"`
	LastName  string `db:"last_name"`
	Length    int    `db:"length"`
}

func (u *LengthUser) DisplayName() string {
	if u.Username != "" {
		return "@" + u.Username
	}
	name := u.FirstName
	if u.LastName != "" {
		name += " " + u.LastName
	}
	if name == "" {
		return "unknown"
	}
	return name
}

func (d *DB) UpsertLengthUser(userID int64, username, firstName, lastName string, length int) error {
	_, err := d.db.Exec(
		`INSERT INTO length_users (user_id, username, first_name, last_name, length) VALUES (?, ?, ?, ?, ?)
		 ON CONFLICT(user_id) DO UPDATE SET username = ?, first_name = ?, last_name = ?, length = ?`,
		userID, username, firstName, lastName, length,
		username, firstName, lastName, length,
	)
	return err
}

func (d *DB) GetTopLengthUsers(limit int) ([]LengthUser, error) {
	var users []LengthUser
	err := d.db.Select(&users, `SELECT * FROM length_users ORDER BY length DESC LIMIT ?`, limit)
	return users, err
}

// --- Buktopuha Players ---

type BuktopuhaPlayer struct {
	UserID      int64  `db:"user_id"`
	Meta        string `db:"meta"`
	GameCounter int    `db:"game_counter"`
	WinCounter  int    `db:"win_counter"`
	TotalScore  int    `db:"total_score"`
	CreatedAt   string `db:"created_at"`
	UpdatedAt   string `db:"updated_at"`
}

func (p *BuktopuhaPlayer) Username() string {
	var meta map[string]any
	_ = json.Unmarshal([]byte(p.Meta), &meta)
	if username, ok := meta["username"].(string); ok && username != "" {
		return username
	}
	firstName, _ := meta["first_name"].(string)
	lastName, _ := meta["last_name"].(string)
	name := firstName
	if lastName != "" {
		if name != "" {
			name += " "
		}
		name += lastName
	}
	if name == "" {
		return "unknown"
	}
	return name
}

func (d *DB) FindBuktopuhaPlayer(userID int64) (*BuktopuhaPlayer, error) {
	var p BuktopuhaPlayer
	err := d.db.Get(&p, `SELECT * FROM buktopuha_players WHERE user_id = ?`, userID)
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func (d *DB) AddBuktopuhaPlayer(userID int64, meta string, score int) error {
	now := time.Now().Format(time.RFC3339)
	winCounter := 0
	if score > 0 {
		winCounter = 1
	}
	_, err := d.db.Exec(
		`INSERT INTO buktopuha_players (user_id, meta, game_counter, win_counter, total_score, created_at, updated_at)
		 VALUES (?, ?, 1, ?, ?, ?, ?)`,
		userID, meta, winCounter, score, now, now,
	)
	return err
}

func (d *DB) IncBuktopuhaWin(userID int64, score int) error {
	now := time.Now().Format(time.RFC3339)
	_, err := d.db.Exec(
		`UPDATE buktopuha_players SET win_counter = win_counter + 1, total_score = total_score + ?, updated_at = ? WHERE user_id = ?`,
		score, now, userID,
	)
	return err
}

func (d *DB) IncBuktopuhaGameCounter(userID int64) error {
	now := time.Now().Format(time.RFC3339)
	_, err := d.db.Exec(
		`UPDATE buktopuha_players SET game_counter = game_counter + 1, updated_at = ? WHERE user_id = ?`,
		now, userID,
	)
	return err
}

func (d *DB) GetAllBuktopuhaPlayers() ([]BuktopuhaPlayer, error) {
	var players []BuktopuhaPlayer
	err := d.db.Select(&players, `SELECT * FROM buktopuha_players ORDER BY win_counter DESC`)
	return players, err
}

// --- AOC Data ---

func (d *DB) GetAOCData() (string, error) {
	var data string
	err := d.db.Get(&data, `SELECT data FROM aoc WHERE id = 0`)
	if err != nil {
		return "", err
	}
	return data, nil
}

func (d *DB) SetAOCData(data string) error {
	_, err := d.db.Exec(
		`INSERT INTO aoc (id, data) VALUES (0, ?) ON CONFLICT(id) DO UPDATE SET data = ?`,
		data, data,
	)
	return err
}
