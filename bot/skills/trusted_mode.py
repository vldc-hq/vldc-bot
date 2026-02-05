import logging
from datetime import datetime
from typing import Optional, Tuple, Any

from pymongo.collection import Collection
from telegram import Update, User
from telegram.ext import Application, ContextTypes

from db.mongo import get_db
from mode import Mode, ON
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

mode = Mode(mode_name="trusted_mode", default=ON)


class DB:
    def __init__(self, db_name: str):
        self._coll: Collection[dict[str, Any]] = get_db(db_name).users

    def get_user(self, user_id: int) -> Optional[dict[str, Any]]:
        return self._coll.find_one(
            {
                "_id": user_id,
            }
        )

    def trust(self, user_id: int, admin_id: int):
        self._coll.insert_one(
            {
                "_id": user_id,
                "by": admin_id,
                "datetime": datetime.now(),
            }
        )

    def untrust(self, user_id: int):
        self._coll.delete_one({"_id": user_id})


_db = DB(db_name="trusted")


App = Application[Any, Any, Any, Any, Any, Any]


def add_trusted_mode(app: App, handlers_group: int):
    logger.info("register trusted-mode handlers")
    app.add_handler(
        ChatCommandHandler(
            "trust",
            trust_callback,
            require_admin=True,
        ),
        group=handlers_group,
    )
    app.add_handler(
        ChatCommandHandler(
            "untrust",
            untrust_callback,
            require_admin=True,
        ),
        group=handlers_group,
    )


def _get_user_and_admin(update: Update) -> Optional[Tuple[User, int, User]]:
    if update.message is None or update.message.reply_to_message is None:
        return None
    user = update.message.reply_to_message.from_user
    admin = update.effective_user
    chat = update.effective_chat
    if user is None or admin is None or chat is None:
        return None
    return user, chat.id, admin


async def trust_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_and_admin(update)
    if data is None:
        return
    user, chat_id, admin = data

    if user and admin and chat_id:
        if _db.get_user(user.id) is not None:
            msg = f"{user.name} is already trusted 😼👍"
        else:
            _db.trust(user.id, admin.id)
            msg = f"{user.name} is trusted now! 😼🤝😐"

        await context.bot.send_message(chat_id, msg)


async def untrust_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_and_admin(update)
    if data is None:
        return
    user, chat_id, _ = data

    if user and chat_id:
        _db.untrust(user.id)
        await context.bot.send_message(chat_id, f"{user.name} lost confidence... 😼🖕")
