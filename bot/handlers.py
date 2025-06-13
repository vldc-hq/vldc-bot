from typing import Callable  # Union can be removed if not used elsewhere

# asyncio removed
# Update removed
from telegram.ext import (
    CommandHandler,
    filters,
)

# RT, CCT, DefaultValue, DEFAULT_FALSE, SLT are removed as they are no longer needed
# from telegram.ext.commandhandler import RT
# from telegram.ext.utils.types import CCT
# from telegram.utils.helpers import DefaultValue, DEFAULT_FALSE
# from telegram.utils.types import SLT

from config import get_group_chat_id


class ChatCommandHandler(CommandHandler):
    """ChatCommandHandler is class-wrapper for `CommandHandler`. It provides default `chat_id` filtering.
    `chat_id` takes from `config.get_group_chat_id() -> str` and it could be either
    chat_username :: str (for public groups) or chat_id :: int (for private or public). So, this wrapper
    support both type of `chat_id`, adds chat_id filtering and set `run_async` to True by default.
    """

    def __init__(
        self,
        command: list[str] | str,  # SLT[str] to list[str] | str
        callback: Callable,  # Callable[[Update, CCT], RT] to Callable
        custom_filters: filters.BaseFilter = None,  # filters: BaseFilter to custom_filters: filters.BaseFilter
        block: bool = True,  # Added block, removed others
        # allow_edited, pass_args, etc. removed
    ):

        # chat_id filtering: accept messages only from particular chat
        chat_id_or_name = get_group_chat_id()
        chat_filter: filters.BaseFilter  # Type hint for clarity
        try:
            chat_filter = filters.Chat(
                chat_id=int(chat_id_or_name)
            )  # Filters.chat to filters.Chat
        except ValueError:
            chat_filter = filters.Chat(
                username=chat_id_or_name.strip("@")
            )  # Filters.chat to filters.Chat

        combined_filters = chat_filter
        if custom_filters:
            combined_filters &= (
                custom_filters  # filters = f if filters is None else filters & f
            )

        # run_async block removed

        super().__init__(
            command,
            callback,
            filters=combined_filters,  # Pass combined_filters
            block=block,  # Pass block
            # Other parameters removed
        )
