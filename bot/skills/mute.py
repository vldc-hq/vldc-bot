import logging
from datetime import datetime, timedelta
from typing import List

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext

from filters import admin_filter

logger = logging.getLogger(__name__)


def add_mute(upd: Updater, handlers_group: int):
    logger.info("registering mute handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("mute", mute, filters=admin_filter), handlers_group)


def _get_minutes(args: List[str]):
    # cmd should be a reply for going to mute user message like "/mute 90"
    return int(args[0])


def mute(update: Update, context: CallbackContext):
    mute_minutes = _get_minutes(context.args)
    until = datetime.now() + timedelta(minutes=mute_minutes)

    try:
        user: User = update.message.reply_to_message.from_user
        logger.info(f"user: {user.full_name}[{user.id}] will be muted for {mute_minutes} min")

        update.message.reply_text(f"Таймаут для {user.full_name} на {mute_minutes} минут")
        context.bot.restrict_chat_member(update.effective_chat.id, user.id, until,
                                         can_add_web_page_previews=False,
                                         can_send_media_messages=False,
                                         can_send_other_messages=False,
                                         can_send_messages=False)
    except Exception as err:
        update.message.reply_text(f"Не вышло :\\ Я точно админ?  \n\n: {err}")
