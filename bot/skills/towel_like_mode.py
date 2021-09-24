import logging
from datetime import datetime, timedelta
from typing import Dict

from pymongo.collection import Collection
from telegram import Update, User
from telegram.ext import (
    CallbackContext,
)

from db.mongo import get_db
from mode import Mode

logger = logging.getLogger(__name__)


# todo: extract maybe?
class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).quarantine

    def add_user(self, user_id: str, ban_time: timedelta):
        return (
            self._coll.insert_one(
                {
                    "_id": user_id,
                    "rel_messages": [],
                    "datetime": datetime.now() + ban_time,
                }
            )
            if self.find_user(user_id) is None
            else None
        )

    def find_user(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def find_all_users(self):
        return self._coll.find({})

    def add_user_rel_message(self, user_id: str, message_id: str):
        self._coll.update_one(
            {"_id": user_id}, {"$addToSet": {"rel_messages": message_id}}
        )

    def delete_user(self, user_id: str):
        return self._coll.delete_one({"_id": user_id})

    def delete_all_users(self):
        return self._coll.delete_many({})


db = DB("towel_like_mode")
mode = Mode(
    mode_name="towel_like_mode",
    default=True,
    off_callback=lambda _: db.delete_all_users(),
)


def _is_time_gone(user: Dict) -> bool:
    return user["datetime"] < datetime.now()


def unquarantine_user(user: User):
    db.delete_user(user_id=user.id)


def quarantine_user(user: User, ban_time: timedelta):
    logger.info("put %s in quarantine", user)
    db.add_user(user.id, ban_time)


def catch_message(update: Update, context: CallbackContext):
    # todo: cache it
    user_id = update.effective_user.id
    user = db.find_user(user_id)
    if user is None:
        return

    if not _is_time_gone(user):
        context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id, 10
        )
    else:
        db.delete_user(user_id=user_id)
