import logging
from typing import Union

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext

logger = logging.getLogger(__name__)


def add_ban(upd: Updater, handlers_group: int):
    logger.info("registering ban handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("ban", ban), handlers_group)


def ban(update: Union[str, Update], context: CallbackContext):
    user: User = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    if user and chat_id:
        context.bot.send_message(chat_id, f'пользователь {user.name} был забанен')
