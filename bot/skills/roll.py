import logging
from datetime import datetime, timedelta
from random import choice
from typing import List

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

logger = logging.getLogger(__name__)

# 24h
MUTE_MINUTES = 1440
BARREL_SIZE = 6


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("roll", roll), handlers_group)


def _get_barrel() -> List[bool]:
    return [choice([True, False]) for _ in range(BARREL_SIZE)]


def _shot() -> bool:
    barrel = _get_barrel()
    logger.info(f"the barrel is {barrel}")
    return choice(barrel)


@run_async
def roll(update: Update, context: CallbackContext):
    user: User = update.effective_user
    is_shoot = _shot()
    logger.info(f"user: {user.full_name}[{user.id}] is rolling and... "
                f"{'miss!' if is_shoot else 'he is dead!'}")
    if is_shoot:
        update.message.reply_text(f"🔫 MISS! 😎")
    else:
        until = datetime.now() + timedelta(minutes=MUTE_MINUTES)
        update.message.reply_text(f"💥 boom! headshot 😵 [24h mute]")
        try:
            context.bot.restrict_chat_member(update.effective_chat.id, user.id, until,
                                             can_add_web_page_previews=False,
                                             can_send_media_messages=False,
                                             can_send_other_messages=False,
                                             can_send_messages=False)
        except Exception as err:
            update.message.reply_text(f"😿 не вышло, потому что: {err}")
