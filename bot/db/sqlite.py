import sqlite3
import logging
import json
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, List, Dict, Iterator, Optional
from config import get_sqlite_db_path

logger = logging.getLogger(__name__)
KISKIS_DAY = 86400
KISKIS_CHAT_PAUSE = 60
KISKIS_FOOD_TIMEOUT = 120


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
            self.db_path = get_sqlite_db_path()
        else:
            self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self) -> Iterator[sqlite3.Connection]:
        with closing(
            sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        ) as conn:
            conn.row_factory = sqlite3.Row
            with conn:
                yield conn

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
            # Kiskis
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS kiskis_users (
                    user_id INTEGER PRIMARY KEY, last_call REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kiskis_chats (
                    chat_id INTEGER PRIMARY KEY, last_call REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kiskis_streaks (
                    chat_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
                    attempts INTEGER NOT NULL, last_attempt REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kiskis_players (
                    chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                    meta TEXT NOT NULL, PRIMARY KEY (chat_id, user_id)
                );
                CREATE TABLE IF NOT EXISTS kiskis_food (
                    token TEXT PRIMARY KEY, chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL, meta TEXT NOT NULL,
                    preferred TEXT NOT NULL, expires REAL NOT NULL,
                    message_id INTEGER, command_id INTEGER NOT NULL
                );
            """)

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

    # --- Kiskis ---
    def kiskis_register_attempt(self, chat_id: int, user_id: int, now: float) -> int:
        with self._get_conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM kiskis_streaks WHERE chat_id=?", (chat_id,)
            ).fetchone()
            attempts = 1
            if (
                row
                and row["user_id"] == user_id
                and now - row["last_attempt"] < KISKIS_DAY
            ):
                attempts = min(3, row["attempts"] + 1)
            conn.execute(
                "INSERT OR REPLACE INTO kiskis_streaks VALUES (?, ?, ?, ?)",
                (chat_id, user_id, attempts, now),
            )
            return attempts

    def kiskis_players(self, chat_id: int, except_user: int) -> list[dict[str, Any]]:
        return [
            json.loads(row[0])
            for row in self.fetchall(
                "SELECT meta FROM kiskis_players WHERE chat_id=? AND user_id!=?",
                (chat_id, except_user),
            )
        ]

    @staticmethod
    def _add_kiskis_reward(conn: sqlite3.Connection, meta: dict[str, Any]) -> None:
        # roll_hussars stores SECONDS, not minutes. Do not increment shot counters.
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO roll_hussars "
            "(user_id, meta, total_time_in_club, first_shot, last_shot) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
            "total_time_in_club=total_time_in_club + excluded.total_time_in_club",
            (meta["id"], json.dumps(meta), KISKIS_DAY, now, now),
        )

    def kiskis_claim(
        self,
        chat_id: int,
        meta: dict[str, Any],
        now: float,
        *,
        reward: dict[str, Any] | None = None,
        food: dict[str, Any] | None = None,
    ) -> tuple[str, float]:
        with self._get_conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT last_call FROM kiskis_users WHERE user_id=?", (meta["id"],)
            ).fetchone()
            if row and now < row[0] + KISKIS_DAY:
                return "personal", row[0] + KISKIS_DAY - now
            row = conn.execute(
                "SELECT last_call FROM kiskis_chats WHERE chat_id=?", (chat_id,)
            ).fetchone()
            if row and now < row[0] + KISKIS_CHAT_PAUSE:
                return "chat", row[0] + KISKIS_CHAT_PAUSE - now
            conn.execute(
                "INSERT OR REPLACE INTO kiskis_users VALUES (?, ?)", (meta["id"], now)
            )
            conn.execute(
                "INSERT OR REPLACE INTO kiskis_chats VALUES (?, ?)", (chat_id, now)
            )
            conn.execute(
                "INSERT OR REPLACE INTO kiskis_players VALUES (?, ?, ?)",
                (chat_id, meta["id"], json.dumps(meta)),
            )
            if reward is not None:
                self._add_kiskis_reward(conn, reward)
            if food is not None:
                conn.execute(
                    "INSERT INTO kiskis_food "
                    "(token, chat_id, user_id, meta, preferred, expires, command_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        food["token"],
                        chat_id,
                        meta["id"],
                        json.dumps(meta),
                        food["preferred"],
                        now + KISKIS_FOOD_TIMEOUT,
                        food["command_id"],
                    ),
                )
            return "ok", 0

    def kiskis_bind_food(self, token: str, message_id: int) -> None:
        self.execute(
            "UPDATE kiskis_food SET message_id=? WHERE token=?", (message_id, token)
        )

    def kiskis_pending_food(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.fetchall("SELECT * FROM kiskis_food")]

    def kiskis_finish_food(
        self,
        token: str,
        now: float,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        selected: str | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        with self._get_conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM kiskis_food WHERE token=?", (token,)
            ).fetchone()
            if row is None:
                return "done", None
            food = dict(row)
            if user_id is not None and (
                user_id != row["user_id"]
                or chat_id != row["chat_id"]
                or message_id != row["message_id"]
            ):
                return "foreign", None
            if now < row["expires"] and selected is None:
                return "pending", None
            if now >= row["expires"]:
                result = "expired"
            else:
                result = "fed" if selected == row["preferred"] else "wrong_food"
            conn.execute("DELETE FROM kiskis_food WHERE token=?", (token,))
            if result == "fed":
                self._add_kiskis_reward(conn, json.loads(row["meta"]))
            return result, food

    # --- Generic helpers ---
    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        with self._get_conn() as conn:
            conn.execute(query, params)

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
