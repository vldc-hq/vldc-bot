import inspect
from typing import Callable, Optional

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, filters as tg_filters

from config import get_group_chat_id
from permissions import is_admin


class ChatCommandHandler(CommandHandler):
    """ChatCommandHandler is class-wrapper for `CommandHandler`. It provides default `chat_id` filtering.
    `chat_id` takes from `config.get_group_chat_id() -> str` and it could be either
    chat_username :: str (for public groups) or chat_id :: int (for private or public). So, this wrapper
    support both type of `chat_id`, adds chat_id filtering and sets block=False by default.
    """

    def __init__(
        self,
        command,
        callback: Callable[[Update, ContextTypes.DEFAULT_TYPE], Optional[object]],
        filters=None,
        require_admin: bool = False,
        block: bool = False,
    ):

        # chat_id filtering: accept messages only from particular chat
        chat_id_or_name = get_group_chat_id()
        if chat_id_or_name:
            try:
                f = tg_filters.Chat(chat_id=int(chat_id_or_name))
            except ValueError:
                f = tg_filters.Chat(username=chat_id_or_name.strip("@"))
            filters = f if filters is None else filters & f

        if require_admin is True:
            callback = _wrap_admin(callback)

        super().__init__(
            command,
            callback,
            filters,
            block=block,
        )


async def _maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result


def _wrap_admin(callback):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await is_admin(update, context):
            return None
        return await _maybe_await(callback(update, context))

    return wrapper
