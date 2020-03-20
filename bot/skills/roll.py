import logging
from datetime import datetime, timedelta
from random import randint
from threading import Lock
from typing import List, Tuple, Dict

import pymongo
import telegram
from pymongo.collection import Collection
from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from db.mongo import get_db
from filters import admin_filter
from mode import cleanup

logger = logging.getLogger(__name__)

MUTE_MINUTES = 16 * 60  # 16h
NUM_BULLETS = 6


class DB:
    """
        Hussar document:
        {
            _id: 420,                                   # int       -- tg user id
            meta: {...},                                # Dict      -- full tg user object (just in case)
            shot_counter: 10,                           # int       -- full amount of shots
            miss_counter: 8,                            # int       -- amount of miss
            dead_counter: 2,                            # int       -- amount of dead shots
            total_time_in_club: datetime(...),          # DateTime  -- all time in the club
            first_shot": datetime(...),                 # DateTIme  -- time of first shot
            "last_shot": datetime(...)                  # DateTIme  -- time of last shot
        }
    """

    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).hussars

    def find_all(self):
        return list(self._coll.find({}).sort("total_time_in_club", pymongo.DESCENDING))

    def find(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def add(self, user: User):
        now: datetime = datetime.now()
        return self._coll.insert_one({
            "_id": user.id,
            "meta": user.to_dict(),
            "shot_counter": 0,
            "miss_counter": 0,
            "dead_counter": 0,
            "total_time_in_club": timedelta().seconds,
            # TODO: wat about ranks?
            # "rank": meh,
            "first_shot": now,
            "last_shot": now,
        })

    def dead(self, user_id: str, mute_min: int):
        self._coll.update_one({"_id": user_id}, {
            "$inc": {"shot_counter": 1, "dead_counter": 1, "total_time_in_club": mute_min * 60},
            "$set": {"last_shot": datetime.now()},
        })

    def miss(self, user_id: str):
        self._coll.update_one({"_id": user_id}, {
            "$inc": {"shot_counter": 1, "miss_counter": 1},
            "$set": {"last_shot": datetime.now()},
        })

    def remove(self, user_id: str):
        self._coll.delete_one({"_id": user_id})

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name='roll')


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("roll", roll), handlers_group)
    dp.add_handler(CommandHandler("gdpr_me", satisfy_GDPR), handlers_group)
    dp.add_handler(CommandHandler("hussars", show_hussars, filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler("wipe_hussars", wipe_hussars, filters=admin_filter), handlers_group)


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
    barrel_str = "".join(misses + chances)
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


def _get_username(h: Dict) -> str:
    """ Get username or fullname or unknown """
    m = h['meta']
    username = m.get('username')
    fname = m.get('first_name')
    lname = m.get('last_name')
    return username or ' '.join(filter(lambda x: x is not None, [fname, lname])) or 'unknown'


@run_async
@cleanup(seconds=600, remove_cmd=True, remove_reply=True)
def show_hussars(update: Update, context: CallbackContext):
    """ Show leader board, I believe it should looks like smth like:

                       Hussars leader board
====================================================
   time in club    | attempts | deaths |      hussar
------------------ + -------- + ------ + -----------
2 days, 15:59:54   | 6        | 6      | egregors
15:59:59           | 1        | 1      | getjump
----------------------------------------------------

    """
    # CSS is awesome!
    # todo:
    #  need to find out how to show board for mobile telegram as well
    board = "```" \
            f"{'Hussars leader board (non mobile friendly)'.center(52)}\n" \
            f"{''.rjust(51, '=')}\n" \
            f"{'time in club'.center(17)} " \
            f"| {'attempts'.center(8)} " \
            f"| {'deaths'.center(6)} " \
            f"| {'hussar'.center(11)} " \
            f"\n" \
            f"{''.ljust(17, '-')} + {''.ljust(8, '-')} + {''.ljust(6, '-')} + {''.ljust(11, '-')}\n"

    for h in _db.find_all():
        username = _get_username(h)
        board += f"{str(timedelta(seconds=(h['total_time_in_club']))).ljust(17)} " \
                 f"| {str(h['shot_counter']).ljust(8)} " \
                 f"| {str(h['dead_counter']).ljust(6)} " \
                 f"| {username.ljust(15)}\n"

    board += f"{''.rjust(51, '-')}\n```"
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"{board}", disable_notification=True,
                             parse_mode=telegram.ParseMode.MARKDOWN)


@run_async
@cleanup(seconds=120, remove_cmd=True, remove_reply=True)
def roll(update: Update, context: CallbackContext):
    user: User = update.effective_user
    # check if hussar already exist or create new one
    _db.find(user_id=user.id) or _db.add(user=user)

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
            # hussar is dead!
            _db.dead(user.id, mute_min)

        except Exception as err:
            # todo: https://github.com/egregors/vldc-bot/issues/93
            #  if bot can't restrict user, user should be passed into towel-mode like state
            update.message.reply_text(f"😿 не вышло, потому что: {err}")
    else:

        # lucky one
        _db.miss(user.id)

        context.bot.send_message(update.effective_chat.id,
                                 f"{user.full_name}: {get_miss_string(shots_remained)}")


# noinspection PyPep8Naming
@run_async
@cleanup(seconds=120, remove_cmd=True, remove_reply=True)
def satisfy_GDPR(update: Update, context: CallbackContext):
    user: User = update.effective_user
    _db.remove(user.id)
    logger.info(f"{user.full_name} was removed from DB")
    update.message.reply_text(f"ok, boomer 😒", disable_notification=True)


@run_async
@cleanup(seconds=120, remove_cmd=True, remove_reply=True)
def wipe_hussars(update: Update, context: CallbackContext):
    _db.remove_all()
    logger.info(f"all hussars was removed from DB")
    update.message.reply_text(f"👍", disable_notification=True)
