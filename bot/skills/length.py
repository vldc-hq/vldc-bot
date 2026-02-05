import logging
from typing import Optional, List, TypedDict, Any, Mapping

import pymongo
from pymongo.collection import Collection
from pymongo.results import UpdateResult
from telegram import Update, User, Message
from telegram.ext import ContextTypes
from typing_utils import App, get_job_queue

from db.mongo import get_db
from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)


class PeninsulaDataType(TypedDict):
    _id: int
    meta: dict[str, Any]


def add_length(app: App, handlers_group: int):
    logger.info("registering length handlers")
    app.add_handler(
        ChatCommandHandler(
            "length",
            _length,
        ),
        group=handlers_group,
    )

    app.add_handler(
        ChatCommandHandler(
            "longest",
            _longest,
        ),
        group=handlers_group,
    )


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection[PeninsulaDataType] = get_db(db_name).peninsulas

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


def _get_username(h: Mapping[str, Any]) -> str:
    """Get username or fullname or unknown."""
    m = h.get("meta", {})
    username = m.get("username")
    fname = m.get("first_name")
    lname = m.get("last_name")
    username = username if isinstance(username, str) else None
    fname = fname if isinstance(fname, str) else None
    lname = lname if isinstance(lname, str) else None
    fullname_parts = [part for part in (fname, lname) if part]
    return username or " ".join(fullname_parts) or "unknown"


async def _length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: User | None = update.effective_user
    if user is None:
        return

    result: Optional[Message] = None

    if update.effective_message is not None:
        result = await update.effective_message.reply_text(
            f"Your telegram id length is {len(str(user.id))} 🍆 ({str(user.id)})"
        )

    _db.add(user)

    cleanup_queue_update(
        get_job_queue(context),
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


async def _longest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = "🍆 🔝🔟 best known lengths 🍆: \n\n"

    n = 1

    for col in _db.get_best_n(10):
        username = _get_username(col)
        message += f"{n} → {username}\n"

        n += 1

    if update.effective_chat is None:
        return
    result: Optional[Message] = await context.bot.send_message(
        update.effective_chat.id,
        message,
        disable_notification=True,
    )

    cleanup_queue_update(
        get_job_queue(context),
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )
