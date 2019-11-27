import logging
from datetime import datetime, timedelta
from random import choice, randint
from threading import Lock

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

logger = logging.getLogger(__name__)

MUTE_MINUTES = 1440  # 24h
NUM_BULLETS = 6


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("roll", roll), handlers_group)


barrel = []
barrel_lock = Lock()


def _reload():
    global barrel
    global barrel_lock

    barrel_lock.acquire()
    empty, bullet = False, True
    barrel = [empty] * NUM_BULLETS
    barrel[randint(0, NUM_BULLETS - 1)] = bullet
    barrel_lock.release()


def _shot():
    global barrel
    global barrel_lock
    barrel_lock.acquire()

    if len(barrel) == 0:
        _reload()

    lucky_number = randint(0, len(barrel) - 1)
    fate = barrel.pop(lucky_number)
    barrel_lock.release()
    return fate


@run_async
def roll(update: Update, context: CallbackContext):
    user: User = update.effective_user
    is_miss = _shot()
    logger.info(f"user: {user.full_name}[{user.id}] is rolling and... "
                f"{'miss!' if is_miss else 'he is dead!'}")
    if is_miss:
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
