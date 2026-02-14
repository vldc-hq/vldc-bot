import os
from typing import Optional, TypedDict


class Config(TypedDict):
    DEBUG: bool
    DEBUGGER: Optional[str]
    TOKEN: str
    AOC_SESSION: Optional[str]
    GROUP_CHAT_ID: Optional[str]
    SQLITE_DB_PATH: str
    SENTRY_DSN: Optional[str]


def get_sqlite_db_path() -> str:
    """Get SQLite database path from ENV"""
    return os.getenv("SQLITE_DB_PATH", "bot.db")


def get_aoc_session() -> Optional[str]:
    """Get AOC session value ENV"""
    return os.getenv("AOC_SESSION", None)


def get_debug() -> bool:
    """Get debug value DEBUG ENV"""
    return os.getenv("DEBUG", "False").lower() == "true"


def get_debugger() -> Optional[str]:
    """Get debugger value DEBUGGER ENV"""
    debugger = os.getenv("DEBUGGER", "")
    return debugger or None


def get_group_chat_id() -> Optional[str]:
    """Get VLDC chat id ENV"""
    chat_id = os.getenv("CHAT_ID", None)
    if chat_id is None:
        return None
    chat_id = chat_id.strip()
    return chat_id or None


def get_token() -> str:
    """Get Telegram bot Token from ENV"""
    token = os.getenv("TOKEN", None)
    if token is None:
        raise ValueError("can't get tg token")
    return token


def get_config() -> Config:
    config: Config = {
        "DEBUG": get_debug(),
        "DEBUGGER": get_debugger(),
        "TOKEN": get_token(),
        "AOC_SESSION": get_aoc_session(),
        "GROUP_CHAT_ID": get_group_chat_id(),
        "SQLITE_DB_PATH": get_sqlite_db_path(),
        "SENTRY_DSN": os.getenv("SENTRY_DSN", None),
    }
    return config
