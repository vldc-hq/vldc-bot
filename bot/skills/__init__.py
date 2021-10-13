import logging
from typing import List, Dict, Callable, Tuple

import toml
from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, Filters

from filters import admin_filter
from mode import cleanup_queue_update
from config import get_group_chat_id
from skills.at_least_70k import add_70k
from skills.ban import add_ban
from skills.banme import add_banme
from skills.coc import add_coc
from skills.core import add_core
from skills.covid_mode import add_covid_mode
from skills.fools import add_fools_mode
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
from skills.uwu import add_uwu

logger = logging.getLogger(__name__)


def _add_version(upd: Updater, version_handlers_group: int):
    logger.info("register version handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "version",
            _version,
            filters=Filters.chat(username=get_group_chat_id().strip("@"))
            & admin_filter,
            run_async=True,
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
        remove_cmd=True,
        remove_reply=False,
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
    # modes
    _make_skill(add_smile_mode, "😼 smile mode", " allow only stickers in the chat"),
    _make_skill(add_since_mode, "🛠 since mode", " under construction"),
    _make_skill(add_towel_mode, "🧼 towel mode", " anti bot"),
    _make_skill(add_fools_mode, "🙃 fools mode", " what? not again!"),
    _make_skill(add_covid_mode, "🦠 covid mode", " fun and gamez"),
    _make_skill(add_nastya_mode, "🤫 nastya mode", " stop. just stop"),
]

commands_list: List[Tuple[str, str]] = [
    ("nya", "😼 Simon says wat?"),
    ("mute", "😼 mute user for N minutes"),
    ("unmute", "😼 unmute user"),
    ("hussars", "😼 show hussars leaderboard"),
    ("wipe_hussars", "😼 wipe all hussars history"),
    ("pr", "got sk1lzz?"),
    ("70k", "try to hire!"),
    ("coc", "VLDC/GDG VL Code of Conduct"),
    ("ban", "ban! ban! ban!"),
    ("roll", "life is so cruel... isn't it?"),
    ("tree", "advent of code time!"),
    ("still", "do u remember it?"),
    ("banme", "commit sudoku"),
    ("prism", "top N PRISM words with optional predicate"),
    ("version", "show this message"),
    ("gdpr_me", "wipe all my hussar history"),
]


def _get_skills_hints(skills_list: List[Dict]) -> str:
    return "\n".join(f"{s['name']} – {s['hint']}" for s in skills_list)
