from typing import Callable, Union

from telegram import Update
from telegram.ext import CommandHandler, BaseFilter, Filters
from telegram.ext.commandhandler import RT
from telegram.ext.utils.types import CCT
from telegram.utils.helpers import DefaultValue, DEFAULT_FALSE
from telegram.utils.types import SLT

from config import get_group_chat_id


class ChatCommandHandler(CommandHandler):
    """ChatCommandHandler is class-wrapper for `CommandHandler`. It provides default `chat_id` filtering.
    `chat_id` takes from `config.get_group_chat_id() -> str` and it could be either
    chat_username :: str (for public groups) or chat_id :: int (for private or public). So, this wrapper
    support both type of `chat_id`, adds chat_id filtering and set `run_async` to True by default.
    """

    def __init__(
        self,
        command: SLT[str],
        callback: Callable[[Update, CCT], RT],
        filters: BaseFilter = None,
        allow_edited: bool = None,
        pass_args: bool = False,
        pass_update_queue: bool = False,
        pass_job_queue: bool = False,
        pass_user_data: bool = False,
        pass_chat_data: bool = False,
        run_async: Union[bool, DefaultValue] = DEFAULT_FALSE,
    ):

        # chat_id filtering: accept messages only from particular chat
        chat_id_or_name = get_group_chat_id()
        try:
            f = Filters.chat(chat_id=int(chat_id_or_name))
        except ValueError:
            f = Filters.chat(username=chat_id_or_name.strip("@"))
        filters = f if filters is None else filters & f

        # run commands async by default
        if run_async == DEFAULT_FALSE:
            run_async = True

        super().__init__(
            command,
            callback,
            filters,
            allow_edited,
            pass_args,
            pass_update_queue,
            pass_job_queue,
            pass_user_data,
            pass_chat_data,
            run_async,
        )
