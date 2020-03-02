import logging
from datetime import datetime, timedelta
from random import randint
from threading import Lock
from typing import List, Tuple

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from mode import cleanup

logger = logging.getLogger(__name__)

MUTE_MINUTES = 16 * 60  # 16h
NUM_BULLETS = 6


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("roll", roll), handlers_group)


barrel_lock = Lock()


def _reload(context: CallbackContext) -> List[bool]:
    empty, bullet = False, True
    barrel: List[bool] = [empty] * NUM_BULLETS
    lucky_number = randint(0, NUM_BULLETS - 1)
    barrel[lucky_number] = bullet
    context.chat_data["barrel"] = barrel

    return barrel


def get_miss_string(shots_remain: int) -> str:
    S = ['😕', '😟', '😥', '😫', '😱']
    misses = ['🔘'] * (NUM_BULLETS - shots_remain)
    chances = ['⚪️'] * shots_remain
    barrel_str = ",".join(misses + chances)
    h = get_mute_minutes(shots_remain - 1) // 60
    return f"{S[NUM_BULLETS - shots_remain - 1]}🔫 MISS! Barrel: {barrel_str}, {h}h"


def get_mute_minutes(shots_remain: int) -> int:
    return MUTE_MINUTES * (NUM_BULLETS - shots_remain)


def _shot(context: CallbackContext) -> Tuple[bool, int]:
    global barrel_lock
    barrel_lock.acquire()

    barrel = context.chat_data.get("barrel")
    if barrel is None or len(barrel) == 0:
        barrel = _reload(context)

    logger.debug(f"barrel before shot: {barrel}")

    fate = barrel.pop()
    context.chat_data["barrel"] = barrel
    shots_remained = len(barrel)  # number before reload
    if fate:
        _reload(context)

    barrel_lock.release()
    return fate, shots_remained


@run_async
@cleanup(seconds=600, remove_cmd=True, remove_reply=True)
def roll(update: Update, context: CallbackContext):
    user: User = update.effective_user

    is_shot, shots_remained = _shot(context)
    logger.info(f"user: {user.full_name}[{user.id}] is rolling and... "
                f"{'he is dead!' if is_shot else 'miss!'}")
    if is_shot:
        mute_min = get_mute_minutes(shots_remained)
        until = datetime.now() + timedelta(minutes=mute_min)
        context.bot.send_message(update.effective_chat.id,
                                 f"💥 boom! {user.full_name} 😵 [{mute_min // 60}h mute]")

        try:
            context.bot.restrict_chat_member(update.effective_chat.id, user.id, until,
                                             can_add_web_page_previews=False,
                                             can_send_media_messages=False,
                                             can_send_other_messages=False,
                                             can_send_messages=False)
        except Exception as err:
            update.message.reply_text(f"😿 не вышло, потому что: {err}")
    else:
        context.bot.send_message(update.effective_chat.id,
                                 f"{user.full_name}: {get_miss_string(shots_remained)}")
