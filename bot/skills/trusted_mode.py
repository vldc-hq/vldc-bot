import logging
from typing import Optional, Tuple, Any

from telegram import Update, User
from telegram.ext import Application, ContextTypes

from db.sqlite import db
from mode import Mode, ON
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

mode = Mode(mode_name="trusted_mode", default=ON)


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
        if db.get_trusted_user(user.id) is not None:
            msg = f"{user.name} is already trusted 😼👍"
        else:
            db.trust_user(user.id, admin.id)
            msg = f"{user.name} is trusted now! 😼🤝😐"

        await context.bot.send_message(chat_id, msg)


async def untrust_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_and_admin(update)
    if data is None:
        return
    user, chat_id, _ = data

    if user and chat_id:
        db.untrust_user(user.id)
        await context.bot.send_message(chat_id, f"{user.name} lost confidence... 😼🖕")
