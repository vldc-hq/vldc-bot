import base64
import json
import logging
from datetime import datetime, timedelta, time
from hashlib import sha1
from operator import itemgetter
from random import choice, random
from timeit import default_timer as timer
from typing import Optional, Tuple

import requests
from pymongo.collection import Collection
from telegram import (Update, User, Bot, Message, UserProfilePhotos, File,
                      PhotoSize, ChatPermissions)
from telegram.error import BadRequest
from telegram.ext import (Updater, CommandHandler, CallbackContext, run_async,
                          JobQueue, MessageHandler)
from telegram.ext.filters import Filters

from config import get_group_chat_id
from db.mongo import get_db
from filters import admin_filter, only_admin_on_others
from mode import cleanup_update_context, cleanup_bot_queue, Mode, OFF
from skills.mute import mute_user_for_time
from skills.roll import _get_username

logger = logging.getLogger(__name__)

QUARANTINE_MINUTES = 16 * 60
QUARANTIN_MUTE_DURATION = timedelta(hours=12)

DAILY_INFECTION_RATE = 0.01

RANDOM_CURE_RATE = 0.01

COUGH_INFECTION_CHANCE_MASKED = 0.01
COUGH_INFECTION_CHANCE_UNMASKED = 0.3

RANDOM_COUGH_INFECTED_CHANCE = 0.1
RANDOM_COUGH_UNINFECTED_CHANCE = 0.002

INFECTION_CHANCE_MASKED = 0.01
INFECTION_CHANCE_UNMASKED = 0.15

LETHALITY_RATE = 0.03

JOB_QUEUE_DAILY_INFECTION_KEY = 'covid_daily_infection_job'
JOB_QUEUE_REPEATING_COUGHING_KEY = 'covid_repeating_coughing_job'

PREV_MESSAGE_USER_KEY = 'prev_message_user'

REPEATING_COUGHING_INTERVAL = timedelta(minutes=1)

DAILY_INFECTION_TIME = time(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
    tzinfo=None)


class DB:
    """
        todo: update scheme
        Members document:
        {
            _id: 420,                                   # int       -- tg user id
            meta: {...},                                # Dict      -- full tg user object (just in case)
            infected_since: datetime(...),              # DateTime  -- time of infection
            quarantined_since: datetime(...),           # DateTime  -- time of infection
            quarantined_until: datetime(...),           # DateTime  -- time of infection
        }

        Settings document:
        {
            covidstatus: True
        }
    """

    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).members

    def find_all(self):
        return list(self._coll.find({}))

    def find(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def add(self, user: User):
        return self._coll.update_one({
            "_id": user.id,
        }, {
            "$set": {"meta": user.to_dict()}
        }, upsert=True)

    def infect(self, user_id: str):
        self._coll.update_one({"_id": user_id}, {
            "$set": {"infected_since": datetime.now()}
        })

    def cure(self, user_id: str):
        self._coll.update_one({"_id": user_id}, {
            "$set": {"cured_since": datetime.now()}
        })

    def is_user_infected(self, user_id: str) -> bool:
        return self._coll.find_one({
            "_id": user_id,
            "infected_since": {"$exists": True},
            "cured_since": {"$exists": False}
        }) is not None

    def add_quarantine(self, user_id: str, since: datetime, until: datetime):
        self._coll.update_one({"_id": user_id}, {
            "$set": {
                "quarantined_since": since,
                "quarantined_until": until
            }
        })

    def add_lethality(self, user_id: str, since: datetime):
        self._coll.update_one({"_id": user_id}, {
            "$set": {
                "lethaled_since": since
            }
        })

    def is_lethaled(self, user_id: str):
        return self._coll.find_one({
            "_id": user_id,
            "lethaled_since": {"$exists": True},
        })

    def remove(self, user_id: str):
        self._coll.delete_one({"_id": user_id})

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name='covid_mode')
mode = Mode(
    mode_name='covid_mode',
    default=OFF,
    on_callback=lambda dp: start_pandemic(dp.job_queue, dp.bot),
    off_callback=lambda dp: cure_all(dp.job_queue, dp.bot)
)


@mode.add
def add_covid_mode(upd: Updater, handlers_group: int):
    logger.info("registering covid handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler(
        "check", test, filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler("infect", infect_admin,
                                  filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler("cough", cough), handlers_group)
    dp.add_handler(CommandHandler("quarantine", quarantine,
                                  filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler(
        "temp", temp, filters=only_admin_on_others), handlers_group)

    # We must do this, since bot api doesnt present a way to get all members
    # of chat at once
    dp.add_handler(MessageHandler(
        Filters.all, callback=catch_message), handlers_group)


def set_handlers(queue: JobQueue, bot: Bot):
    queue.run_daily(lambda _: daily_infection(get_group_chat_id(), bot),
                    DAILY_INFECTION_TIME,
                    name=JOB_QUEUE_DAILY_INFECTION_KEY)

    queue.run_repeating(lambda _: random_cough(bot, queue),
                        REPEATING_COUGHING_INTERVAL,
                        name=JOB_QUEUE_REPEATING_COUGHING_KEY)


def cure_all(queue: JobQueue, bot: Bot) -> None:
    # wipe db and ununrestrict all infected users
    for user in _db.find_all():
        # unrestrict all except admins (they are so good)
        try:
            # TODO: extract it more properly
            unmute_perm = ChatPermissions(
                can_add_web_page_previews=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_messages=True
            )
            bot.restrict_chat_member(get_group_chat_id(), user.id, unmute_perm)
            logger.debug(f"user: {_get_username(user)} was unrestrict")
        except Exception as err:
            logger.warning(f"can't unrestrict {_get_username(user)}: {err}")
    _db.remove_all()

    # clean up the jobs queue
    covid_daily_infection_job: Tuple = queue.get_jobs_by_name(
        JOB_QUEUE_DAILY_INFECTION_KEY)

    if covid_daily_infection_job:
        covid_daily_infection_job[0].schedule_removal()

    covid_repeating_coughing_job: Tuple = queue.get_jobs_by_name(
        JOB_QUEUE_REPEATING_COUGHING_KEY)

    if covid_repeating_coughing_job:
        covid_repeating_coughing_job[0].schedule_removal()


def start_pandemic(queue: JobQueue, bot: Bot) -> None:
    set_handlers(queue, bot)

    bot.send_message(get_group_chat_id(), f"ALARM!!! CORONAVIRUS IS SPREADING")


@run_async
def temp(update: Update, context: CallbackContext):
    message: Message = update.message
    user: User = message.from_user

    if message.reply_to_message:
        user = message.reply_to_message.from_user

    mdb_user = _db.find(user.id)

    temp_appendix = .0

    if mdb_user is not None:
        if 'infected_since' in mdb_user:
            days_count = (datetime.now() - mdb_user['infected_since']).days
            temp_appendix = random() * min(max(days_count / 4, 3), 1)

    if temp_appendix == 0:
        temp_appendix = random() + 1.5 * random()

    temp = str(round(36 + temp_appendix, 2))

    message.reply_text(f"У {user.full_name} температура {temp} С")


@run_async
def quarantine(update: Update, context: CallbackContext):
    try:
        user: User = update.message.reply_to_message.from_user
        update.message.reply_text(
            f"{user.full_name} помещён в карантин на {QUARANTIN_MUTE_DURATION}")
        since = datetime.now()
        until = since + QUARANTIN_MUTE_DURATION
        _db.add_quarantine(user.id, since, until)
        mute_user_for_time(update, context, user, QUARANTIN_MUTE_DURATION)
    except Exception as err:
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")


@run_async
def test(update: Update, context: CallbackContext):
    reply_user: User = update.message.reply_to_message.from_user

    if _db.is_user_infected(reply_user.id):
        update.message.reply_text(f"😿 {reply_user.full_name} инфицирован")
    else:
        update.message.reply_text(f"{reply_user.full_name} здоров")


@run_async
@cleanup_update_context(seconds=600)
def cough(update: Update, context: CallbackContext):
    user: User = update.effective_user

    if update.message.reply_to_message is None:
        update.message.reply_text(f"{user.full_name} чихнул в пространство")
        return

    reply_user: User = update.message.reply_to_message.from_user

    update.message.reply_text(
        f"{user.full_name} чихнул на {reply_user.full_name}")

    if _db.is_user_infected(user.id):
        infect_user_masked_condition(
            reply_user,
            COUGH_INFECTION_CHANCE_MASKED,
            COUGH_INFECTION_CHANCE_UNMASKED,
            context)


@run_async
@cleanup_update_context(seconds=600)
def infect_admin(update: Update, context: CallbackContext):
    infect_user: User = update.message.reply_to_message.from_user
    _db.add(infect_user)
    _db.infect(infect_user.id)
    update.message.reply_text(
        f"{update.effective_user.full_name} опрокинул колбу с коронавирусом на {infect_user.full_name}")


@run_async
@cleanup_bot_queue(seconds=60)
def random_cough(bot: Bot, queue: JobQueue):
    users = _db.find_all()

    message = ''

    for user in users:
        _rng = random()

        # todo: move "_get_username" to commons
        full_name = _get_username(user)

        lethaled = _db.is_lethaled(user['_id'])

        if 'infected_since' in user and 'cured_since' not in user and lethaled is None:
            chance = RANDOM_COUGH_INFECTED_CHANCE
            delta_seconds = (datetime.now() - user['infected_since']).total_seconds()
            delta_days_float = delta_seconds / (60 * 60 * 24)

            if _rng <= RANDOM_CURE_RATE ** (2 - delta_days_float):
                chance = .0
                _db.cure(user['_id'])
                message += f"{full_name} излечился от коронавируса\n"

            if _rng <= LETHALITY_RATE * (delta_days_float ** delta_days_float):
                chance = .0
                try:
                    _db.add_lethality(user['_id'], datetime.now())
                    # TODO: Extract it more properly
                    mute_perm = ChatPermissions(
                        can_add_web_page_previews=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_send_messages=False
                    )
                    bot.restrict_chat_member(get_group_chat_id(), user['_id'], mute_perm)
                    message += f"{full_name} умер от коронавируса, F\n"

                except BadRequest as err:
                    err_msg = f"can't restrict user: {err}"
                    logger.warning(err_msg)
        else:
            chance = RANDOM_COUGH_UNINFECTED_CHANCE

        if _rng <= chance:
            message += f"{full_name} чихнул в пространство \n"

    if message:
        bot.send_message(get_group_chat_id(), message)


def get_single_user_photo(user: User) -> bytearray:
    photos: UserProfilePhotos = user.get_profile_photos()
    result: bytearray = bytearray()

    if len(photos.photos) > 0:
        if len(photos.photos[0]) == 0:
            return bytearray(b'\x00')
        photo: PhotoSize = sorted(
            photos.photos[0], key=itemgetter('width'), reverse=True)[0]
        file_photo: File = photo.get_file()
        result = file_photo.download_as_bytearray()

    return result


def infect_user_masked_condition(user: User, masked_probability: float, unmasked_probability: float,
                                 context: CallbackContext):
    if user is None:
        return

    has_mask = False
    photo_bytearray = get_single_user_photo(user)

    if get_single_user_photo(user) is not [0]:
        has_mask = is_avatar_has_mask(
            photo_bytearray, user, context)

    _rng = random()
    logger.debug(_rng)

    if has_mask:
        infecting = _rng <= masked_probability
    else:
        infecting = _rng <= unmasked_probability

    logger.debug(infecting)
    if infecting:
        logger.debug(f"User {user.full_name} infected")
        _db.infect(user.id)


def catch_message(update: Update, context: CallbackContext):
    user: User = update.effective_user

    if update.message is not None and update.message.reply_to_message is not None:
        _db.add(update.message.reply_to_message.from_user)

    user_to_infect: Optional[User] = None

    if PREV_MESSAGE_USER_KEY in context.chat_data.keys():
        prev_message_user: User = context.chat_data[PREV_MESSAGE_USER_KEY]

        if _db.is_user_infected(user.id):
            user_to_infect = prev_message_user
        if _db.is_user_infected(prev_message_user.id):
            user_to_infect = user

    infect_user_masked_condition(
        user_to_infect, INFECTION_CHANCE_MASKED, INFECTION_CHANCE_UNMASKED, context)

    context.chat_data[PREV_MESSAGE_USER_KEY] = user

    _db.add(user)


def hash_img(img: bytearray) -> str:
    return sha1(img[-100:]).hexdigest()


def container_predict(img: bytearray, key: str) -> bool:
    encoded_image = base64.b64encode(img).decode('utf-8')
    instances = {
        'instances': [
            {'image_bytes': {'b64': str(encoded_image)},
             'key': key}
        ]
    }

    url = 'http://serving:8501/v1/models/default:predict'
    start = timer()
    response = requests.post(url, data=json.dumps(instances)).json()
    logger.info(f"inference time is {timer() - start}")
    hasMask = sorted(zip(response['predictions'][0]['labels'],
                         response['predictions'][0]['scores']),
                     key=lambda x: -x[1])[0][0] == 'good'
    return hasMask


def is_avatar_has_mask(img: bytearray, user: User, context: CallbackContext) -> bool:
    if (img is None) or len(img) < 100:
        return False

    # lookup existing value in cache
    cache_key = 'avatar_mask_cache'
    hash_ = hash_img(img)
    if cache_key in context.bot_data.keys():
        is_good = context.bot_data[cache_key].get(hash_)
        if is_good is not None:
            return is_good

    try:
        is_good = container_predict(img, hash_)

        if cache_key not in context.bot_data.keys():
            context.bot_data[cache_key] = {}

        context.bot_data[cache_key][hash_] = is_good
        message = f"User {user.full_name} {'has' if is_good else 'does not have'} mask on"
        context.bot.send_message(get_group_chat_id(), message)
        return is_good

    except Exception as err:
        logger.error(f"can't check mask: {err}")
        return False


def daily_infection(chat_id, bot: Bot):
    members_count = bot.getChatMembersCount(chat_id)
    users = _db.find_all()
    infect_count = max(int(DAILY_INFECTION_RATE * members_count), 1)

    for _ in range(infect_count):
        infect_member = choice(users)
        _db.infect(infect_member["_id"])
