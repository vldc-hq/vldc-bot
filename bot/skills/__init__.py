import logging
from typing import List, Callable, Tuple, TypedDict

from telegram import Update
from telegram.ext import ContextTypes
from handlers import ChatCommandHandler
from mode import cleanup_queue_update
from typing_utils import App, get_job_queue
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
from skills.buktopuha import add_buktopuha
from skills.chat import add_chat_mode

logger = logging.getLogger(__name__)
VERSION = "0.13.0"


class Skill(TypedDict):
    name: str
    add_handlers: Callable[[App, int], None]
    hint: str


def _add_version(app: App, version_handlers_group: int) -> None:
    logger.info("register version handlers")
    app.add_handler(
        ChatCommandHandler(
            "version",
            _version,
            require_admin=True,
        ),
        group=version_handlers_group,
    )


async def _version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show a current version of bot"""

    logger.info("current ver.: %s", VERSION)

    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id

    result = await context.bot.send_message(
        chat_id,
        f"~=~~=~=~=_ver.:{VERSION}_~=~=~=[,,_,,]:3\n\n" f"{_get_skills_hints(skills)}",
    )

    job_queue = get_job_queue(context)
    cleanup_queue_update(
        job_queue,
        update.message,
        result,
        120,
    )


def _make_skill(
    add_handlers: Callable[[App, int], None], name: str, hint: str
) -> Skill:
    return {"name": name, "add_handlers": add_handlers, "hint": hint}


skills: List[Skill] = [
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
    _make_skill(add_buktopuha, "🤫 start BukToPuHa", " let's play a game"),
    # modes
    _make_skill(add_trusted_mode, "👁‍🗨 in god we trust", " are you worthy hah?"),
    _make_skill(add_aoc_mode, "🎄 AOC notifier", " kekV"),
    _make_skill(add_smile_mode, "😼 smile mode", " allow only stickers in the chat"),
    _make_skill(add_since_mode, "🛠 since mode", " under construction"),
    _make_skill(add_towel_mode, "🧼 towel mode", " anti bot"),
    _make_skill(add_fools_mode, "🙃 fools mode", " what? not again!"),
    _make_skill(add_nastya_mode, "🤫 nastya mode", " stop. just stop"),
    _make_skill(add_chat_mode, "😼 chat", " chat"),
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
    ("kozula", "💰 kozula: Don't argue with kozula rate!"),
    ("still", "do u remember it?"),
    ("banme", "commit sudoku"),
    ("prism", "top N PRISM words with optional predicate"),
    ("version", "show this message"),
    ("gdpr_me", "wipe all my hussar history"),
    ("length", "length of your instrument"),
    ("longest", "size doesn't matter, or is it?"),
    ("buktopuha", "let's play a game 🤡"),
    ("znatoki", "top BuKToPuHa players"),
]


def _get_skills_hints(skills_list: List[Skill]) -> str:
    return "\n".join(f"{s['name']} – {s['hint']}" for s in skills_list)
