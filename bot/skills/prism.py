import logging
from datetime import datetime
from typing import TypedDict

import pymongo
from pymongo.collection import Collection
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import MessageHandler, ContextTypes, filters

from tg_filters import group_chat_filter
from db.mongo import get_db
from mode import cleanup_queue_update
from handlers import ChatCommandHandler
from typing_utils import App, get_job_queue

logger = logging.getLogger(__name__)

DEFAULT_TOP_LIMIT = 10


class WordRecord(TypedDict):
    word: str
    count: int
    last_use: datetime


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection[WordRecord] = get_db(db_name).words

    def add_word(self, word: str):
        self._coll.update_one(
            {"word": word},
            {"$inc": {"count": 1}, "$set": {"last_use": datetime.now()}},
            upsert=True,
        )

    def add_words(self, words: list[str]) -> None:
        for word in words:
            self.add_word(word)

    def find_all(self) -> list["WordRecord"]:
        return list(self._coll.find({}).sort("count", pymongo.DESCENDING))


_db = DB(db_name="words")


def add_prism(app: App, handlers_group: int):
    logger.info("register words handlers")
    app.add_handler(
        ChatCommandHandler(
            "top",
            show_top,
            require_admin=True,
        ),
        group=handlers_group,
    )
    group_filter = group_chat_filter()
    app.add_handler(
        MessageHandler(
            filters.TEXT & group_filter,
            extract_words,
            block=False,
        ),
        group=handlers_group,
    )


async def extract_words(update: Update, _: ContextTypes.DEFAULT_TYPE):
    if update.message is not None:
        text = update.message.text
    elif update.edited_message is not None:
        text = update.edited_message.text
    else:
        return
    if text is None:
        return
    _db.add_words(_normalize_words(_get_words(text)))


def _get_words(t: str) -> list[str]:
    return t.split(" ")


def _normalize_words(words: list[str]) -> list[str]:
    return [w.lower() for w in words if len(w) > 0 and w[0] != "/"]


def _normalize_pred(pred: str) -> str:
    return pred.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")


def _get_pred(context: ContextTypes.DEFAULT_TYPE) -> str:
    args = context.args or []
    return " ".join(args) if len(args) > 0 else "True"


def _eval_filter(words: list["WordRecord"], pred: str) -> list["WordRecord"]:
    def inner_pred(word: "WordRecord") -> bool:
        w = word["word"]
        c = word["count"]
        # pylint: disable=eval-used
        return eval("lambda w, c: " + _normalize_pred(pred))(w, c)

    return list(filter(inner_pred, words.copy()))


async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    default_words = _db.find_all()

    try:
        words = _eval_filter(default_words, _get_pred(context))
    except (ValueError, TypeError) as err:
        logger.exception(err)
        words = default_words

    top = "\n".join([f"{w['word']}: {w['count']}" for w in words[:DEFAULT_TOP_LIMIT]])
    if update.effective_chat is None:
        return
    result = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"```\n{top}\n```",
        disable_notification=True,
        parse_mode=ParseMode.MARKDOWN,
    )

    cleanup_queue_update(
        get_job_queue(context),
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )
