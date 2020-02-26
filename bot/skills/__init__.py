import logging
from typing import List, Dict, Callable

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, run_async

from filters import admin_filter
from mode import cleanup
from skills.banme import add_banme
from skills.core import add_core
from skills.fools import add_fools_mode
from skills.mute import add_mute
from skills.roll import add_roll
from skills.since_mode import add_since_mode
from skills.smile_mode import add_smile_mode
from skills.still import add_still
from skills.towel_mode import add_towel_mode
from skills.tree import add_tree
from skills.uwu import add_uwu
from skills.coc import add_coc

__version__ = "0.13"

logger = logging.getLogger(__name__)


def _add_version(upd: Updater, version_handlers_group: int):
    logger.info("register version handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("version", _version,
                                  filters=admin_filter), version_handlers_group)


@run_async
@cleanup(seconds=20, remove_cmd=True)
def _version(update: Update, context: CallbackContext):
    """ Show current version of bot """
    logger.info(f"current ver.: {__version__}")

    chat_id = update.effective_chat.id

    context.bot.send_message(
        chat_id, f"~=~~=~=~=_ver.:{__version__}_~=~=~=[,,_,,]:3\n\n"
                 f"{_get_skills_hints(skills)}")


def _make_skill(add_handlers: Callable, name: str, hint: str) -> Dict:
    return {
        "name": name,
        "add_handlers": add_handlers,
        "hint": hint
    }


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

    # modes
    _make_skill(add_smile_mode, "😼 smile mode",
                " allow only stickers in the chat"),
    _make_skill(add_since_mode, "🛠 since mode", " under construction"),
    _make_skill(add_towel_mode, "🧼 towel mode", " anti bot"),
    _make_skill(add_fools_mode, "🙃 fools mode", " what? not again!"),
]


def _get_skills_hints(skills_list: List[Dict]) -> str:
    return "\n".join(f"{s['name']} – {s['hint']}" for s in skills_list)
