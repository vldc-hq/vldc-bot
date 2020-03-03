import logging
from datetime import datetime, timedelta
from random import randint
from threading import Lock
from typing import List, Tuple, Dict

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
        return list(self._coll.find({}))

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

    def dead(self, user_id: str, until: datetime):
        ban_duration = until - datetime.now()
        self._coll.update_one({"_id": user_id}, {
            "$inc": {"shot_counter": 1, "dead_counter": 1, "total_time_in_club": ban_duration.seconds},
            "$set": {"last_shot": datetime.now()},
        })

    def miss(self, user_id: str):
        self._coll.update_one({"_id": user_id}, {
            "$inc": {"shot_counter": 1, "miss_counter": 1},
            "$set": {"last_shot": datetime.now()},
        })


_db = DB(db_name='roll')


def add_roll(upd: Updater, handlers_group: int):
    logger.info("registering roll handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("roll", roll), handlers_group)
    dp.add_handler(CommandHandler("hussars", show_hussars, filters=admin_filter), handlers_group)


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
    misses = ["x"] * (NUM_BULLETS - shots_remain)
    chances = ["?"] * shots_remain
    barrel_str = ",".join(misses + chances)
    h = get_mute_minutes(shots_remain - 1) // 60
    return f"{S[NUM_BULLETS - shots_remain - 1]}🔫 MISS! Barrel: ({barrel_str}), {h}h"


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
def show_hussars(update: Update, context: CallbackContext):
    """ Show leader board, I believe it should looks like smth like:

    Доска почетных гусаров
    ======================
    [3 days 12:74:12] KittyHawk1 200 | 150
    [12:48:00] Egregors 1 | 1

    """

    hs: List[Dict] = _db.find_all()
    board: str = "Доска почетных гусаров\n===================\n\n"
    for h in hs:
        board += f"[{timedelta(seconds=(h['total_time_in_club']))}] " \
                 f"{h['meta']['username']} " \
                 f"{h['shot_counter']} | {h['dead_counter']}\n"

    update.message.reply_text(f"{board}")


@run_async
@cleanup(seconds=600, remove_cmd=True, remove_reply=True)
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

        # hussar is dead!
        _db.dead(user.id, until)

        try:
            context.bot.restrict_chat_member(update.effective_chat.id, user.id, until,
                                             can_add_web_page_previews=False,
                                             can_send_media_messages=False,
                                             can_send_other_messages=False,
                                             can_send_messages=False)
        except Exception as err:
            # todo: https://github.com/egregors/vldc-bot/issues/93
            #  if bot can't restrict user, user should be passed into towel-mode like state
            update.message.reply_text(f"😿 не вышло, потому что: {err}")
    else:

        # lucky one
        _db.miss(user.id)

        context.bot.send_message(update.effective_chat.id,
                                 f"{user.full_name}: {get_miss_string(shots_remained)}")
