import sqlite3
import json
import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
MONGO_USER = os.getenv("MONGO_INITDB_ROOT_USERNAME", "root")
MONGO_PASS = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "secret")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "bot.db")

mongo_client = MongoClient(f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}")
sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
sqlite_conn.row_factory = sqlite3.Row

def init_sqlite_schema():
    print(f"Ensuring schema exists in {SQLITE_DB_PATH}...")
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS trusted_users (
            user_id INTEGER PRIMARY KEY,
            "by" INTEGER,
            datetime DATETIME
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS buktopuha_players (
            user_id INTEGER PRIMARY KEY,
            meta TEXT,
            game_counter INTEGER DEFAULT 0,
            win_counter INTEGER DEFAULT 0,
            total_score INTEGER DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS towel_quarantine (
            user_id INTEGER PRIMARY KEY,
            rel_messages TEXT,
            datetime DATETIME
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS since_topics (
            topic TEXT PRIMARY KEY,
            since_datetime DATETIME,
            count INTEGER DEFAULT 0
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS roll_hussars (
            user_id INTEGER PRIMARY KEY,
            meta TEXT,
            shot_counter INTEGER DEFAULT 0,
            miss_counter INTEGER DEFAULT 0,
            dead_counter INTEGER DEFAULT 0,
            total_time_in_club INTEGER DEFAULT 0,
            first_shot DATETIME,
            last_shot DATETIME
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS prism_words (
            word TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_use DATETIME
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS peninsula_users (
            user_id INTEGER PRIMARY KEY,
            meta TEXT
        )
    """)
    sqlite_conn.execute("""
        CREATE TABLE IF NOT EXISTS aoc (
            id INTEGER PRIMARY KEY CHECK (id = 0),
            data TEXT
        )
    """)
    sqlite_conn.commit()

def migrate_trusted():
    print("Migrating trusted_users...")
    db = mongo_client.trusted
    for user in db.users.find():
        sqlite_conn.execute(
            'INSERT OR REPLACE INTO trusted_users (user_id, "by", datetime) VALUES (?, ?, ?)',
            (user["_id"], user["by"], user["datetime"])
        )
    sqlite_conn.commit()

def migrate_buktopuha():
    print("Migrating buktopuha_players...")
    db = mongo_client.buktopuha
    for player in db.players.find():
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO buktopuha_players (user_id, meta, game_counter, win_counter, total_score, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (player["_id"], json.dumps(player["meta"]), player["game_counter"], player["win_counter"], player["total_score"], player["created_at"], player["updated_at"])
        )
    sqlite_conn.commit()

def migrate_towel():
    print("Migrating towel_quarantine...")
    db = mongo_client.towel_mode
    for q in db.quarantine.find():
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO towel_quarantine (user_id, rel_messages, datetime) VALUES (?, ?, ?)",
            (q["_id"], json.dumps(q["rel_messages"]), q["datetime"])
        )
    sqlite_conn.commit()

def migrate_since():
    print("Migrating since_topics...")
    db = mongo_client.since_mode
    for t in db.topics.find():
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO since_topics (topic, since_datetime, count) VALUES (?, ?, ?)",
            (t["topic"], t["since_datetime"], t["count"])
        )
    sqlite_conn.commit()

def migrate_roll():
    print("Migrating roll_hussars...")
    db = mongo_client.roll
    for h in db.hussars.find():
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO roll_hussars (user_id, meta, shot_counter, miss_counter, dead_counter, total_time_in_club, first_shot, last_shot) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (h["_id"], json.dumps(h["meta"]), h["shot_counter"], h["miss_counter"], h["dead_counter"], h["total_time_in_club"], h["first_shot"], h["last_shot"])
        )
    sqlite_conn.commit()

def migrate_prism():
    print("Migrating prism_words...")
    db = mongo_client.words
    for w in db.words.find():
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO prism_words (word, count, last_use) VALUES (?, ?, ?)",
            (w["word"], w["count"], w["last_use"])
        )
    sqlite_conn.commit()

def migrate_peninsulas():
    print("Migrating peninsula_users...")
    db = mongo_client.peninsulas
    for p in db.peninsulas.find():
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO peninsula_users (user_id, meta) VALUES (?, ?)",
            (p["_id"], json.dumps(p["meta"]))
        )
    sqlite_conn.commit()

def migrate_aoc():
    print("Migrating aoc...")
    db = mongo_client.aoc
    data = db.aoc.find_one()
    if data:
        data.pop("_id", None)
        sqlite_conn.execute(
            "INSERT OR REPLACE INTO aoc (id, data) VALUES (0, ?)",
            (json.dumps(data),)
        )
    sqlite_conn.commit()

if __name__ == "__main__":
    init_sqlite_schema()
    migrate_trusted()
    migrate_buktopuha()
    migrate_towel()
    migrate_since()
    migrate_roll()
    migrate_prism()
    migrate_peninsulas()
    migrate_aoc()
    print("\nMigration finished successfully!")
    print(f"SQLite database is ready at: {SQLITE_DB_PATH}")
