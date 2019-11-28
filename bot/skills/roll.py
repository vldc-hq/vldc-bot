import logging
from datetime import datetime, timedelta
from random import choice, randint, seed
from threading import Lock

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async
from typing import List, Tuple

logger = logging.getLogger(__name__)

MUTE_MINUTES = 8 * 60  # 8h
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


def get_miss_string(shots_remain: int) -> str:
    S = ['😕', '😟', '😥', '😫', '😱']
    misses = ["x"] * (NUM_BULLETS - shots_remain)
    chances = ["?"] * shots_remain
    barrel_str = ",".join(misses + chances)
    h = get_mute_minutes(shots_remain - 1) // 60
    return f"MISS! {S[NUM_BULLETS - shots_remain-1]}🔫. Current barrel: ({barrel_str}), {h}h"


def get_mute_minutes(shots_remain: int) -> int:
    return MUTE_MINUTES * (NUM_BULLETS - shots_remain)


def _shot(chat_id: str, context: CallbackContext) -> Tuple[bool, int]:
    global barrel_lock
    barrel_lock.acquire()

    barrel = context.chat_data.get("barrel")
    if barrel is None or len(barrel) == 0:
        barrel = _reload(chat_id, context)

    logger.debug(f"barrel before shot: {barrel}")

    fate = barrel.pop()
    context.chat_data["barrel"] = barrel
    shots_remained = len(barrel)  # number before reload
    if fate:
        _reload(chat_id, context)
    barrel_lock.release()
    return (fate, shots_remained)


@run_async
def roll(update: Update, context: CallbackContext):
    user: User = update.effective_user
    is_shot, shots_remained = _shot(update.effective_chat.id, context)
    logger.info(f"user: {user.full_name}[{user.id}] is rolling and... "
                f"{'he is dead!' if is_shot else 'miss!'}")
    mute_min = get_mute_minutes(shots_remained)
    if is_shot:
        mute_min = get_mute_minutes(shots_remained)
        until = datetime.now() + timedelta(minutes=mute_min)
        update.message.reply_text(
            f"💥 boom! headshot 😵 [{mute_min//60}h mute]")
        try:
            context.bot.restrict_chat_member(update.effective_chat.id, user.id, until,
                                             can_add_web_page_previews=False,
                                             can_send_media_messages=False,
                                             can_send_other_messages=False,
                                             can_send_messages=False)
        except Exception as err:
            update.message.reply_text(f"😿 не вышло, потому что: {err}")
    else:
        update.message.reply_text(get_miss_string(shots_remained))
