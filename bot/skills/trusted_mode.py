import logging
from datetime import datetime
from typing import Optional

# asyncio removed
from pymongo.collection import Collection
from telegram import Update, User
from telegram.ext import Application, CallbackContext

from db.mongo import get_db
from filters import admin_filter
from mode import Mode, ON
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

mode = Mode(mode_name="trusted_mode", default=ON)


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).users

    def get_user(self, user_id: int) -> Optional[dict]:
        return self._coll.find_one(
            {
                "_id": user_id,
            }
        )

    def trust(self, user_id: str, admin_id: str):
        self._coll.insert_one(
            {
                "_id": user_id,
                "by": admin_id,
                "datetime": datetime.now(),
            }
        )

    def untrust(self, user_id):
        self._coll.delete_one({"_id": user_id})


_db = DB(db_name="trusted")


def add_trusted_mode(application: Application, handlers_group: int):
    logger.info("register trusted-mode handlers")
    application.add_handler(
        ChatCommandHandler(
            "trust",
            trust_callback,
            custom_filters=admin_filter,
        ),
        handlers_group,
    )
    application.add_handler(
        ChatCommandHandler(
            "untrust",
            untrust_callback,
            custom_filters=admin_filter,
        ),
        handlers_group,
    )


def _get_user_and_admin(update) -> (str, str, str):
    user: User = update.message.reply_to_message.from_user
    admin: User = update.effective_user
    chat_id = update.effective_chat.id
    return user, chat_id, admin


async def trust_callback(update: Update, context: CallbackContext):
    user, chat_id, admin = _get_user_and_admin(update)

    if user and admin and chat_id:
        if _db.get_user(user.id) is not None:
            msg = f"{user.name} is already trusted 😼👍"
        else:
            _db.trust(user.id, admin.id)
            msg = f"{user.name} is trusted now! 😼🤝😐"

        await context.bot.send_message(chat_id, msg)


async def untrust_callback(update: Update, context: CallbackContext):
    user, chat_id, _ = _get_user_and_admin(update)

    if user and chat_id:
        _db.untrust(user.id)
        await context.bot.send_message(chat_id, f"{user.name} lost confidence... 😼🖕")
