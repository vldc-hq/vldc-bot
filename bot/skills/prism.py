import logging
from datetime import datetime
from typing import List, Dict

import asyncio
import pymongo
import telegram
from pymongo.collection import Collection
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
)

from config import get_group_chat_id
from db.mongo import get_db
from filters import admin_filter
from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

DEFAULT_TOP_LIMIT = 10


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).words

    def add_word(self, word: str):
        self._coll.update_one(
            {"word": word},
            {"$inc": {"count": 1}, "$set": {"last_use": datetime.now()}},
            upsert=True,
        )

    def add_words(self, words: List[str]):
        for word in words:
            self.add_word(word)

    def find_all(self) -> list[str]:
        return list(self._coll.find({}).sort("count", pymongo.DESCENDING))


_db = DB(db_name="words")


def add_prism(application: Application, handlers_group: int):
    logger.info("register words handlers")
    application.add_handler(
        ChatCommandHandler(
            "top",
            show_top,
            filters=admin_filter,
        ),
        handlers_group,
    )
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Chat(username=get_group_chat_id().strip("@")),
            extract_words,
        ),
        handlers_group,
    )


async def extract_words(update: Update, _: CallbackContext):
    text = update.message.text if update.message else update.edited_message.text
    _db.add_words(_normalize_words(_get_words(text)))


def _get_words(t: str) -> List[str]:
    return t.split(" ")


def _normalize_words(words: List[str]) -> List[str]:
    return [w.lower() for w in words if len(w) > 0 and w[0] != "/"]


def _normalize_pred(pred: str) -> str:
    return pred.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")


def _get_pred(context: CallbackContext) -> str:
    return " ".join(context.args) if len(context.args) > 0 else "True"


def _eval_filter(words: List[Dict], pred: str):
    def inner_pred(word):
        w = word["word"]
        c = word["count"]
        # pylint: disable=eval-used
        return eval("lambda w, c: " + _normalize_pred(pred))(w, c)

    return list(filter(inner_pred, words.copy()))


async def show_top(update: Update, context: CallbackContext):
    default_words = _db.find_all()

    try:
        words = _eval_filter(default_words, _get_pred(context))
    except (ValueError, TypeError) as err:
        logger.exception(err)
        words = default_words

    top = "\n".join([f"{w['word']}: {w['count']}" for w in words[:DEFAULT_TOP_LIMIT]])
    result = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"```\n{top}\n```",
        disable_notification=True,
        parse_mode=telegram.ParseMode.MARKDOWN,
    )

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )
