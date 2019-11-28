import logging
from datetime import datetime, timedelta
from random import choice, randint, seed
from threading import Lock

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async
from typing import List

logger = logging.getLogger(__name__)

MUTE_MINUTES = 1440  # 24h
NUM_BULLETS = 6


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("roll", roll), handlers_group)


barrel_lock = Lock()


def _reload(chat_id: str, context: CallbackContext) -> List[bool]:
    empty, bullet = False, True
    barrel: List[bool] = []
    barrel = [empty] * NUM_BULLETS
    lucky_number = randint(0, NUM_BULLETS - 1)
    barrel[lucky_number] = bullet
    context.chat_data["barrel"] = barrel

    return barrel


def get_miss_string(context: CallbackContext) -> str:
    S = ['😕', '😟', '😥', '😫', '😱']
    barrel = context.chat_data.get("barrel")
    if barrel is None:
        return "[?,?,?,?,?,?]"
    misses = ["x"] * (NUM_BULLETS - len(barrel))
    chances = ["?"] * len(barrel)
    barrel_str = ",".join(misses + chances)
    return f"🔫 MISS! {S[NUM_BULLETS - len(barrel)-1]}. Current barrel: ({barrel_str})"


def _shot(chat_id: str, context: CallbackContext):
    global barrel_lock
    barrel_lock.acquire()

    barrel = context.chat_data.get("barrel")
    if barrel is None or len(barrel) == 0:
        barrel = _reload(chat_id, context)

    logger.debug(f"barrel before shot: {barrel}")

    fate = barrel.pop()
    context.chat_data["barrel"] = barrel
    if fate:
        _reload(chat_id, context)
    barrel_lock.release()
    return fate


@run_async
def roll(update: Update, context: CallbackContext):

    user: User = update.effective_user
    is_shot = _shot(update.effective_chat.id, context)
    logger.info(f"user: {user.full_name}[{user.id}] is rolling and... "
                f"{'he is dead!' if is_shot else 'miss!'}")
    if is_shot:
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
    else:
        update.message.reply_text(get_miss_string(context))
