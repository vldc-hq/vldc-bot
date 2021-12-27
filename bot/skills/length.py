import logging
from typing import Optional, List, TypedDict

from telegram import Update, User, Message, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.ext.filters import Filters

from mode import cleanup_queue_update
from config import get_group_chat_id

from skills.roll import _get_username

from db.mongo import get_db
import pymongo
from pymongo.collection import Collection
from pymongo.results import UpdateResult

logger = logging.getLogger(__name__)


class PeninsulaDataType(TypedDict):
    _id: str
    meta: User


def add_length(upd: Updater, handlers_group: int):
    logger.info("registering length handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "length",
            _length,
            filters=Filters.chat(username=get_group_chat_id().strip("@")),
            run_async=True,
        ),
        handlers_group,
    )

    dp.add_handler(
        CommandHandler(
            "longest",
            _longest,
            filters=Filters.chat(username=get_group_chat_id().strip("@")),
            run_async=True,
        ),
        handlers_group,
    )


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).peninsulas

    def get_best_n(self, n: int = 10) -> List[PeninsulaDataType]:
        return list(self._coll.find({}).sort("_id", pymongo.ASCENDING).limit(n))

    def add(self, user: User) -> UpdateResult:
        return self._coll.update_one(
            {
                "_id": int(user.id),
            },
            {
                "$set": {
                    "meta": user.to_dict(),
                }
            },
            upsert=True,
        )


_db = DB(db_name="peninsulas")


def _length(update: Update, context: CallbackContext):
    user: User = update.effective_user

    result: Optional[Message] = None

    if update.effective_message is not None:
        result = update.effective_message.reply_text(
            f"Your telegram id length is {len(str(user.id))} 🍆 ({str(user.id)})"
        )

    _db.add(user)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


def _longest(update: Update, context: CallbackContext):
    message = "🍆 🔝🔟 best known lengths 🍆: \n\n"

    n = 1

    for col in _db.get_best_n(10):
        username = _get_username(col)
        message += f"{n} → {username}\n"

        n += 1

    result: Optional[Message] = context.bot.send_message(
        update.effective_chat.id,
        message,
        disable_notification=True,
    )

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )
