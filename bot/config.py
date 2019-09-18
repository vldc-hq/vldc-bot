import os
from typing import Dict, Union


def get_debug() -> Union[str, bool]:
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


def get_mongo_user():
    user = os.getenv("MONGO_INITDB_ROOT_USERNAME", None)
    if user is None:
        raise ValueError("can't get mongodb username")
    return user


def get_mongo_pass():
    user = os.getenv("MONGO_INITDB_ROOT_PASSWORD", None)
    if user is None:
        raise ValueError("can't get mongodb password")
    return user


def get_config() -> Dict:
    return {
        "DEBUG": get_debug(),
        "TOKEN": get_token(),
        "GROUP_CHAT_ID": get_group_chat_id(),
        "MONGO_USER": get_mongo_user(),
        "MONGO_PASS": get_mongo_pass()
    }
