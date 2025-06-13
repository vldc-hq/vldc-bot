import logging
from typing import Optional, List, TypedDict

import asyncio
import pymongo
from pymongo.collection import Collection
from pymongo.results import UpdateResult
from telegram import Update, User, Message
from telegram.ext import Application, CallbackContext

from db.mongo import get_db
from mode import cleanup_queue_update
from handlers import ChatCommandHandler
from skills.roll import _get_username

logger = logging.getLogger(__name__)


class PeninsulaDataType(TypedDict):
    _id: str
    meta: User


def add_length(application: Application, handlers_group: int):
    logger.info("registering length handlers")
    application.add_handler(
        ChatCommandHandler(
            "length",
            _length,
        ),
        handlers_group,
    )

    dp.add_handler(
        ChatCommandHandler(
            "longest",
            _longest,
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


async def _length(update: Update, context: CallbackContext):
    user: User = update.effective_user

    result: Optional[Message] = None

    if update.effective_message is not None:
        result = await update.effective_message.reply_text(
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


async def _longest(update: Update, context: CallbackContext):
    message = "🍆 🔝🔟 best known lengths 🍆: \n\n"

    n = 1

    for col in _db.get_best_n(10):
        username = _get_username(col)
        message += f"{n} → {username}\n"

        n += 1

    result: Optional[Message] = await context.bot.send_message(
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
