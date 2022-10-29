import logging
from datetime import timedelta
from random import randint

from telegram import Update, User, TelegramError
from telegram.ext import Updater, CallbackContext

from skills import ChatCommandHandler
from skills.mute import mute_user_for_time

MUTE_MINUTES = 24 * 60  # 24h
MIN_MULT = 1
MAX_MULT = 7

logger = logging.getLogger(__name__)


def get_mute_minutes() -> timedelta:
    return timedelta(minutes=randint(MIN_MULT, MAX_MULT) * MUTE_MINUTES)


def add_banme(upd: Updater, handlers_group: int):
    logger.info("registering banme handlers")
    dp = upd.dispatcher
    dp.add_handler(ChatCommandHandler("banme", banme), handlers_group)


def banme(update: Update, context: CallbackContext):
    try:
        user: User = update.message.from_user
        mute_user_for_time(update, context, user, get_mute_minutes())
    except TelegramError as err:
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")
