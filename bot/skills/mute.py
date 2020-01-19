import logging
from datetime import datetime, timedelta
from typing import List

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext

from filters import admin_filter
from utils.time import get_duration

logger = logging.getLogger(__name__)


def add_mute(upd: Updater, handlers_group: int):
    logger.info("registering mute handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("mute", mute, filters=admin_filter), handlers_group)


def _get_minutes(args: List[str]):
    # cmd should be a reply for going to mute user message like "/mute 90"
    if len(args) < 1:
        raise Exception("mute cmd should be a reply for going to mute user message like '/mute 90', "
                        "where '90' is duration of the mute")
    return get_duration(args[0])


def mute_user_for_time(update: Update, context: CallbackContext, user: User, mute_duration: timedelta):
    try:
        until = datetime.now() + mute_duration
        logger.info(f"user: {user.full_name}[{user.id}] will be muted for {mute_duration}")

        update.message.reply_text(f"Таймаут для {user.full_name} на {mute_duration}")
        context.bot.restrict_chat_member(update.effective_chat.id, user.id,
                                         until,
                                         can_add_web_page_previews=False,
                                         can_send_media_messages=False,
                                         can_send_other_messages=False,
                                         can_send_messages=False)
    except Exception as err:
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")


def mute(update: Update, context: CallbackContext):
    try:
        mute_minutes = _get_minutes(context.args)
        user: User = update.message.reply_to_message.from_user
        mute_user_for_time(update, context, user, mute_minutes)
    except Exception as err:
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")
