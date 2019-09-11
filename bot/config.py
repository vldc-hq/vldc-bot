import os
from typing import Dict


def get_debug() -> bool:
    return os.getenv("DEBUG", False)


def get_group_chat_id() -> str:
    """ Get VLDC chat id ENV """
    chat_id = os.getenv("CHAT_ID", None)
    if chat_id is None:
        raise ValueError("can't get CHAT_ID")
    return chat_id


def get_token() -> str:
    """ Get Telegram bot Token from ENV """
    token = os.getenv("TOKEN", None)
    if token is None:
        raise ValueError("can't get tg token")
    return token


def get_config() -> Dict:
    return {
        "DEBUG": get_debug(),
        "TOKEN": get_token(),
        "GROUP_CHAT_ID": get_group_chat_id()
    }
