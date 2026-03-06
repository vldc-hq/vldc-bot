-- +goose Up
CREATE TABLE IF NOT EXISTS trusted_users (
    user_id INTEGER PRIMARY KEY,
    "by" INTEGER,
    datetime DATETIME
);

CREATE TABLE IF NOT EXISTS buktopuha_players (
    user_id INTEGER PRIMARY KEY,
    meta TEXT,
    game_counter INTEGER DEFAULT 0,
    win_counter INTEGER DEFAULT 0,
    total_score INTEGER DEFAULT 0,
    created_at DATETIME,
    updated_at DATETIME
);

CREATE TABLE IF NOT EXISTS towel_quarantine (
    user_id INTEGER PRIMARY KEY,
    rel_messages TEXT,
    datetime DATETIME
);

CREATE TABLE IF NOT EXISTS since_topics (
    topic TEXT PRIMARY KEY,
    since_datetime DATETIME,
    count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS roll_hussars (
    user_id INTEGER PRIMARY KEY,
    meta TEXT,
    shot_counter INTEGER DEFAULT 0,
    miss_counter INTEGER DEFAULT 0,
    dead_counter INTEGER DEFAULT 0,
    total_time_in_club INTEGER DEFAULT 0,
    first_shot DATETIME,
    last_shot DATETIME
);

CREATE TABLE IF NOT EXISTS prism_words (
    word TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0,
    last_use DATETIME
);

CREATE TABLE IF NOT EXISTS peninsula_users (
    user_id INTEGER PRIMARY KEY,
    meta TEXT
);

CREATE TABLE IF NOT EXISTS aoc (
    id INTEGER PRIMARY KEY CHECK (id = 0),
    data TEXT
);

-- +goose Down
DROP TABLE IF EXISTS aoc;
DROP TABLE IF EXISTS peninsula_users;
DROP TABLE IF EXISTS prism_words;
DROP TABLE IF EXISTS roll_hussars;
DROP TABLE IF EXISTS since_topics;
DROP TABLE IF EXISTS towel_quarantine;
DROP TABLE IF EXISTS buktopuha_players;
DROP TABLE IF EXISTS trusted_users;
