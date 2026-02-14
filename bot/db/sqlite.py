import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Any, List, Dict, Optional
from config import get_config

logger = logging.getLogger(__name__)


# Register adapters for datetime
def adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()


def convert_datetime(s: bytes) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s.decode())
    except ValueError, TypeError:
        return None


sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("DATETIME", convert_datetime)


# pylint: disable=too-many-public-methods
class BotDB:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            conf = get_config()
            self.db_path = conf["SQLITE_DB_PATH"]
        else:
            self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        logger.info("Initializing SQLite database at %s", self.db_path)
        with self._get_conn() as conn:
            # Trusted Users
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trusted_users (
                    user_id INTEGER PRIMARY KEY,
                    "by" INTEGER,
                    datetime DATETIME
                )
            """)
            # Buktopuha Players
            conn.execute("""
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
            # Towel Quarantine
            conn.execute("""
                CREATE TABLE IF NOT EXISTS towel_quarantine (
                    user_id INTEGER PRIMARY KEY,
                    rel_messages TEXT,
                    datetime DATETIME
                )
            """)
            # Since Topics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS since_topics (
                    topic TEXT PRIMARY KEY,
                    since_datetime DATETIME,
                    count INTEGER DEFAULT 0
                )
            """)
            # Roll Hussars
            conn.execute("""
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
            # Prism Words
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prism_words (
                    word TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0,
                    last_use DATETIME
                )
            """)
            # Peninsula Users
            conn.execute("""
                CREATE TABLE IF NOT EXISTS peninsula_users (
                    user_id INTEGER PRIMARY KEY,
                    meta TEXT
                )
            """)
            # AOC Data
            conn.execute("""
                CREATE TABLE IF NOT EXISTS aoc (
                    id INTEGER PRIMARY KEY CHECK (id = 0),
                    data TEXT
                )
            """)
            conn.commit()

    # --- Trusted Users ---
    def get_trusted_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = self.fetchone("SELECT * FROM trusted_users WHERE user_id = ?", (user_id,))
        return dict(row) if row else None

    def trust_user(self, user_id: int, admin_id: int) -> None:
        self.execute(
            'INSERT OR REPLACE INTO trusted_users (user_id, "by", datetime) VALUES (?, ?, ?)',
            (user_id, admin_id, datetime.now()),
        )

    def untrust_user(self, user_id: int) -> None:
        self.execute("DELETE FROM trusted_users WHERE user_id = ?", (user_id,))

    def is_user_trusted(self, user_id: int | str) -> bool:
        row = self.fetchone("SELECT 1 FROM trusted_users WHERE user_id = ?", (user_id,))
        return row is not None

    # --- Buktopuha ---
    def get_all_buktopuha_players(self) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM buktopuha_players ORDER BY win_counter DESC"
        )
        res: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["_id"] = d.pop("user_id")
            d["meta"] = json.loads(d["meta"])
            res.append(d)
        return res

    def find_buktopuha_player(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = self.fetchone(
            "SELECT * FROM buktopuha_players WHERE user_id = ?", (user_id,)
        )
        if row:
            d = dict(row)
            d["_id"] = d.pop("user_id")
            d["meta"] = json.loads(d["meta"])
            return d
        return None

    def add_buktopuha_player(
        self, user_id: int, user_meta: Dict[str, Any], score: int = 0
    ) -> None:
        now = datetime.now()
        game_inc = 1 if score == 0 else 0
        win_inc = 1 if score > 0 else 0
        self.execute(
            "INSERT INTO buktopuha_players (user_id, meta, game_counter, win_counter, total_score, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, json.dumps(user_meta), game_inc, win_inc, score, now, now),
        )

    def inc_buktopuha_game_counter(self, user_id: int) -> None:
        self.execute(
            "UPDATE buktopuha_players SET game_counter = game_counter + 1, updated_at = ? WHERE user_id = ?",
            (datetime.now(), user_id),
        )

    def inc_buktopuha_win(self, user_id: int, score: int) -> None:
        self.execute(
            "UPDATE buktopuha_players SET win_counter = win_counter + 1, total_score = total_score + ?, updated_at = ? WHERE user_id = ?",
            (score, datetime.now(), user_id),
        )

    def remove_buktopuha_player(self, user_id: int) -> None:
        self.execute("DELETE FROM buktopuha_players WHERE user_id = ?", (user_id,))

    def remove_all_buktopuha_players(self) -> None:
        self.execute("DELETE FROM buktopuha_players")

    # --- Towel Quarantine ---
    def add_quarantine_user(self, user_id: int, quarantine_time_min: int) -> None:
        if self.find_quarantine_user(user_id) is not None:
            return
        self.execute(
            "INSERT INTO towel_quarantine (user_id, rel_messages, datetime) VALUES (?, ?, ?)",
            (
                user_id,
                json.dumps([]),
                datetime.now() + timedelta(minutes=quarantine_time_min),
            ),
        )

    def find_quarantine_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = self.fetchone(
            "SELECT * FROM towel_quarantine WHERE user_id = ?", (user_id,)
        )
        if row:
            d = dict(row)
            d["_id"] = d.pop("user_id")
            d["rel_messages"] = json.loads(d["rel_messages"])
            return d
        return None

    def find_all_quarantine_users(self) -> List[Dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM towel_quarantine")
        res: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["_id"] = d.pop("user_id")
            d["rel_messages"] = json.loads(d["rel_messages"])
            res.append(d)
        return res

    def add_quarantine_rel_message(self, user_id: int, message_id: int) -> None:
        user = self.find_quarantine_user(user_id)
        if user:
            rel_messages = set(user["rel_messages"])
            rel_messages.add(message_id)
            self.execute(
                "UPDATE towel_quarantine SET rel_messages = ? WHERE user_id = ?",
                (json.dumps(list(rel_messages)), user_id),
            )

    def delete_quarantine_user(self, user_id: int) -> None:
        self.execute("DELETE FROM towel_quarantine WHERE user_id = ?", (user_id,))

    def delete_all_quarantine_users(self) -> None:
        self.execute("DELETE FROM towel_quarantine")

    # --- Since Topics ---
    def get_since_topic(self, topic: str) -> Dict[str, Any]:
        row = self.fetchone(
            "SELECT * FROM since_topics WHERE topic = ?", (topic.lower(),)
        )
        if row:
            return dict(row)
        return {"topic": topic.lower(), "since_datetime": datetime.now(), "count": 1}

    def update_since_topic(
        self, topic: str, since_datetime: datetime, count: int
    ) -> None:
        row = self.fetchone(
            "SELECT 1 FROM since_topics WHERE topic = ?", (topic.lower(),)
        )
        if row:
            self.execute(
                "UPDATE since_topics SET count = count + 1, since_datetime = ? WHERE topic = ?",
                (datetime.now(), topic.lower()),
            )
        else:
            self.execute(
                "INSERT INTO since_topics (topic, since_datetime, count) VALUES (?, ?, ?)",
                (topic.lower(), since_datetime, count),
            )

    def get_all_since_topics(self, limit: int) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM since_topics ORDER BY count DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in rows]

    # --- Roll Hussars ---
    def get_all_hussars(self) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM roll_hussars ORDER BY total_time_in_club DESC"
        )
        res: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["_id"] = d.pop("user_id")
            d["meta"] = json.loads(d["meta"])
            res.append(d)
        return res

    def find_hussar(self, user_id: int) -> Optional[Dict[str, Any]]:
        row = self.fetchone("SELECT * FROM roll_hussars WHERE user_id = ?", (user_id,))
        if row:
            d = dict(row)
            d["_id"] = d.pop("user_id")
            d["meta"] = json.loads(d["meta"])
            return d
        return None

    def add_hussar(self, user_id: int, user_meta: Dict[str, Any]) -> None:
        now = datetime.now()
        self.execute(
            "INSERT INTO roll_hussars (user_id, meta, shot_counter, miss_counter, dead_counter, total_time_in_club, first_shot, last_shot) VALUES (?, ?, 0, 0, 0, 0, ?, ?)",
            (user_id, json.dumps(user_meta), now, now),
        )

    def hussar_dead(self, user_id: int, mute_min: int) -> None:
        self.execute(
            "UPDATE roll_hussars SET shot_counter = shot_counter + 1, dead_counter = dead_counter + 1, total_time_in_club = total_time_in_club + ?, last_shot = ? WHERE user_id = ?",
            (mute_min * 60, datetime.now(), user_id),
        )

    def hussar_miss(self, user_id: int) -> None:
        self.execute(
            "UPDATE roll_hussars SET shot_counter = shot_counter + 1, miss_counter = miss_counter + 1, last_shot = ? WHERE user_id = ?",
            (datetime.now(), user_id),
        )

    def remove_hussar(self, user_id: int) -> None:
        self.execute("DELETE FROM roll_hussars WHERE user_id = ?", (user_id,))

    def remove_all_hussars(self) -> None:
        self.execute("DELETE FROM roll_hussars")

    # --- Prism Words ---
    def add_prism_word(self, word: str) -> None:
        row = self.fetchone("SELECT 1 FROM prism_words WHERE word = ?", (word.lower(),))
        if row:
            self.execute(
                "UPDATE prism_words SET count = count + 1, last_use = ? WHERE word = ?",
                (datetime.now(), word.lower()),
            )
        else:
            self.execute(
                "INSERT INTO prism_words (word, count, last_use) VALUES (?, 1, ?)",
                (word.lower(), datetime.now()),
            )

    def get_all_prism_words(self) -> List[Dict[str, Any]]:
        rows = self.fetchall("SELECT * FROM prism_words ORDER BY count DESC")
        return [dict(r) for r in rows]

    # --- Peninsula Users ---
    def get_best_peninsulas(self, n: int = 10) -> List[Dict[str, Any]]:
        rows = self.fetchall(
            "SELECT * FROM peninsula_users ORDER BY user_id ASC LIMIT ?", (n,)
        )
        res: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["_id"] = d.pop("user_id")
            d["meta"] = json.loads(d["meta"])
            res.append(d)
        return res

    def add_peninsula_user(self, user_id: int, user_meta: Dict[str, Any]) -> None:
        self.execute(
            "INSERT OR REPLACE INTO peninsula_users (user_id, meta) VALUES (?, ?)",
            (user_id, json.dumps(user_meta)),
        )

    # --- AOC Data ---
    def update_aoc_data(self, data: Dict[str, Any]) -> None:
        self.execute(
            "INSERT OR REPLACE INTO aoc (id, data) VALUES (0, ?)",
            (json.dumps(data),),
        )

    def get_aoc_data(self) -> Optional[Dict[str, Any]]:
        row = self.fetchone("SELECT data FROM aoc WHERE id = 0")
        if row:
            return json.loads(row["data"])
        return None

    def remove_all_aoc_data(self) -> None:
        self.execute("DELETE FROM aoc")

    # --- Generic helpers ---
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        with self._get_conn() as conn:
            return conn.execute(query, params)

    def fetchone(
        self, query: str, params: tuple[Any, ...] = ()
    ) -> Optional[sqlite3.Row]:
        with self._get_conn() as conn:
            return conn.execute(query, params).fetchone()

    def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        with self._get_conn() as conn:
            return conn.execute(query, params).fetchall()


# Global instance
db = BotDB()
