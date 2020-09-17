import logging
from datetime import datetime
from typing import List

from pymongo.collection import Collection
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, run_async

from db.mongo import get_db

logger = logging.getLogger(__name__)


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).words

    def add_word(self, word: str):
        self._coll.update_one({"word": word}, {
            "$inc": {"count": 1},
            "$set": {"last_use": datetime.now()}
        }, upsert=True)

    def add_words(self, words: List[str]):
        for word in words:
            self.add_word(word)


_db = DB(db_name='words')


def add_words(upd: Updater, handlers_group: int):
    logger.info("register words handlers")
    dp = upd.dispatcher
    dp.add_handler(MessageHandler(Filters.text, extract_words), handlers_group)


@run_async
def extract_words(update: Update, context: CallbackContext):
    _db.add_words(_normalize(_get_words(update.message.text)))


def _get_words(t: str) -> List[str]:
    return t.split(' ')


def _normalize(words: List[str]) -> List[str]:
    return [w.lower() for w in words]
