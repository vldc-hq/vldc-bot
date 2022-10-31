import logging
from typing import List, Dict, Callable, Tuple, Union

import toml
from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, Filters, BaseFilter
from telegram.ext.commandhandler import RT
from telegram.ext.utils.types import CCT
from telegram.utils.helpers import DefaultValue, DEFAULT_FALSE
from telegram.utils.types import SLT

from config import get_group_chat_id
from filters import admin_filter
from mode import cleanup_queue_update
from skills.aoc_mode import add_aoc_mode
from skills.at_least_70k import add_70k
from skills.ban import add_ban
from skills.banme import add_banme
from skills.coc import add_coc
from skills.core import add_core
from skills.fools import add_fools_mode
from skills.kozula import add_kozula
from skills.length import add_length
from skills.mute import add_mute
from skills.nastya_mode import add_nastya_mode
from skills.nya import add_nya
from skills.pr import add_pr
from skills.prism import add_prism
from skills.roll import add_roll
from skills.since_mode import add_since_mode
from skills.smile_mode import add_smile_mode
from skills.still import add_still
from skills.towel_mode import add_towel_mode
from skills.tree import add_tree
from skills.trusted_mode import add_trusted_mode
from skills.uwu import add_uwu

logger = logging.getLogger(__name__)


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


def _add_version(upd: Updater, version_handlers_group: int):
    logger.info("register version handlers")
    dp = upd.dispatcher
    dp.add_handler(
        ChatCommandHandler(
            "version",
            _version,
            filters=admin_filter,
        ),
        version_handlers_group,
    )


def _get_version_from_pipfile() -> str:
    """Parse toml file for version"""
    with open("Pipfile", "r") as pipfile:
        toml_dict = toml.loads(pipfile.read())
    version = toml_dict["description"][0]["version"]
    return version


def _version(update: Update, context: CallbackContext):
    """Show a current version of bot"""

    version = _get_version_from_pipfile()

    logger.info("current ver.: %s", version)

    chat_id = update.effective_chat.id

    result = context.bot.send_message(
        chat_id,
        f"~=~~=~=~=_ver.:{version}_~=~=~=[,,_,,]:3\n\n" f"{_get_skills_hints(skills)}",
    )

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
    )


def _make_skill(add_handlers: Callable, name: str, hint: str) -> Dict:
    return {"name": name, "add_handlers": add_handlers, "hint": hint}


skills: List[Dict] = [
    # commands
    _make_skill(add_core, "😼 core", " core"),
    _make_skill(_add_version, "😼 version", " show this message"),
    _make_skill(add_still, "😻 still", "do u remember it?"),
    _make_skill(add_uwu, "😾 uwu", " don't uwu!"),
    _make_skill(add_mute, "🤭 mute", " mute user for N minutes"),
    _make_skill(add_roll, "🔫 roll", " life is so cruel... isn't it?"),
    _make_skill(add_banme, "⚔️ banme", " commit sudoku"),
    _make_skill(add_tree, "🎄 tree", " advent of code time!"),
    _make_skill(add_coc, "⛔🤬 coc", " VLDC/GDG VL Code of Conduct"),
    _make_skill(add_70k, "🛠 more than 70k?", " try to hire!"),
    _make_skill(add_pr, "💻 got sk1lzz?", " put them to use!"),
    _make_skill(add_prism, "👁 smell like PRISM?", " nononono!"),
    _make_skill(add_ban, "🔨 ban!", " ban! ban! ban!"),
    _make_skill(add_nya, "😺 meow", " Simon says wat?"),
    _make_skill(add_kozula, "💰 kozula", " Don't argue with kozula rate!"),
    _make_skill(add_length, "🍆 length", " length of your instrument"),
    # modes
    _make_skill(add_trusted_mode, "👁‍🗨 in god we trust", " are you worthy hah?"),
    _make_skill(add_aoc_mode, "🎄 AOC notifier", " kekV"),
    _make_skill(add_smile_mode, "😼 smile mode", " allow only stickers in the chat"),
    _make_skill(add_since_mode, "🛠 since mode", " under construction"),
    _make_skill(add_towel_mode, "🧼 towel mode", " anti bot"),
    _make_skill(add_fools_mode, "🙃 fools mode", " what? not again!"),
    _make_skill(add_nastya_mode, "🤫 nastya mode", " stop. just stop"),
]

commands_list: List[Tuple[str, str]] = [
    ("nya", "😼 Simon says wat?"),
    ("mute", "😼 mute user for N minutes"),
    ("unmute", "😼 unmute user"),
    ("hussars", "😼 show hussars leaderboard"),
    ("wipe_hussars", "😼 wipe all hussars history"),
    ("trust", "😼 in god we trust"),
    ("untrust", "😼 how dare you?!"),
    ("pr", "got sk1lzz?"),
    ("70k", "try to hire!"),
    ("coc", "VLDC/GDG VL Code of Conduct"),
    ("ban", "ban! ban! ban!"),
    ("roll", "life is so cruel... isn't it?"),
    ("tree", "advent of code time!"),
    ("kozula", "💰 kozula", " Don't argue with kozula rate!"),
    ("still", "do u remember it?"),
    ("banme", "commit sudoku"),
    ("prism", "top N PRISM words with optional predicate"),
    ("version", "show this message"),
    ("gdpr_me", "wipe all my hussar history"),
    ("length", "length of your instrument"),
    ("longest", "size doesn't matter, or is it?"),
]


def _get_skills_hints(skills_list: List[Dict]) -> str:
    return "\n".join(f"{s['name']} – {s['hint']}" for s in skills_list)
