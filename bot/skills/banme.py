import logging
from datetime import timedelta
from random import randint

from telegram import Update, User
from telegram.error import TelegramError
from telegram.ext import Application, ContextTypes

from handlers import ChatCommandHandler
from skills.mute import mute_user_for_time

MUTE_MINUTES = 24 * 60  # 24h
MIN_MULT = 1
MAX_MULT = 7

logger = logging.getLogger(__name__)


def get_mute_minutes() -> timedelta:
    return timedelta(minutes=randint(MIN_MULT, MAX_MULT) * MUTE_MINUTES)


def add_banme(app: Application, handlers_group: int):
    logger.info("registering banme handlers")
    app.add_handler(ChatCommandHandler("banme", banme), group=handlers_group)


async def banme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message is None or update.message.from_user is None:
            return
        user: User = update.message.from_user
        await mute_user_for_time(update, context, user, get_mute_minutes())
    except TelegramError as err:
        await update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")
