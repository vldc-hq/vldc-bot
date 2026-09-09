"""Bounded game state; claims and rewards are committed in one transaction."""

import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

DAY = 86400
CHAT_PAUSE = 60
FOOD_TIMEOUT = 120


class KiskisStore:
    def __init__(self, path: str):
        self.path = path
        with self.transaction() as conn:
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

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with closing(self.connect()) as conn:
            with conn:
                yield conn

    def register_attempt(self, chat_id: int, user_id: int, now: float) -> int:
        with self.transaction() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM kiskis_streaks WHERE chat_id=?", (chat_id,)
            ).fetchone()
            attempts = 1
            if row and row["user_id"] == user_id and now - row["last_attempt"] < DAY:
                attempts = min(3, row["attempts"] + 1)
            conn.execute(
                "INSERT OR REPLACE INTO kiskis_streaks VALUES (?, ?, ?, ?)",
                (chat_id, user_id, attempts, now),
            )
            return attempts

    def players(self, chat_id: int, except_user: int) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            return [
                json.loads(row[0])
                for row in conn.execute(
                    "SELECT meta FROM kiskis_players WHERE chat_id=? AND user_id!=?",
                    (chat_id, except_user),
                )
            ]

    @staticmethod
    def reward(conn: sqlite3.Connection, meta: dict[str, Any]) -> None:
        # roll_hussars stores SECONDS, not minutes. Do not increment shot counters.
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO roll_hussars "
            "(user_id, meta, total_time_in_club, first_shot, last_shot) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET "
            "total_time_in_club=total_time_in_club + excluded.total_time_in_club",
            (meta["id"], json.dumps(meta), DAY, now, now),
        )

    def claim(
        self,
        chat_id: int,
        meta: dict[str, Any],
        now: float,
        *,
        reward: dict[str, Any] | None = None,
        food: dict[str, Any] | None = None,
    ) -> tuple[str, float]:
        with self.transaction() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT last_call FROM kiskis_users WHERE user_id=?", (meta["id"],)
            ).fetchone()
            if row and now < row[0] + DAY:
                return "personal", row[0] + DAY - now
            row = conn.execute(
                "SELECT last_call FROM kiskis_chats WHERE chat_id=?", (chat_id,)
            ).fetchone()
            if row and now < row[0] + CHAT_PAUSE:
                return "chat", row[0] + CHAT_PAUSE - now
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
                self.reward(conn, reward)
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
                        now + FOOD_TIMEOUT,
                        food["command_id"],
                    ),
                )
            return "ok", 0

    def bind_food(self, token: str, message_id: int) -> None:
        with self.transaction() as conn:
            conn.execute(
                "UPDATE kiskis_food SET message_id=? WHERE token=?", (message_id, token)
            )

    def pending_food(self) -> list[dict[str, Any]]:
        with closing(self.connect()) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM kiskis_food")]

    def finish_food(
        self,
        token: str,
        now: float,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        message_id: int | None = None,
        selected: str | None = None,
    ) -> tuple[str, dict[str, Any] | None]:
        with self.transaction() as conn:
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
                self.reward(conn, json.loads(row["meta"]))
            return result, food
