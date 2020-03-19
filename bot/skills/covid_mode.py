import logging
from datetime import datetime, timedelta, time
from random import choice, random
from hashlib import sha1

from pymongo.collection import Collection
from telegram import (Update, User, Bot, Message, UserProfilePhotos, File,
                      PhotoSize)
from telegram.ext import (Updater, CommandHandler, CallbackContext, run_async,
                          JobQueue, MessageHandler)
from telegram.ext.filters import Filters

from google.cloud import automl_v1beta1
from google.cloud.automl_v1beta1.proto import service_pb2

from db.mongo import get_db
from filters import admin_filter, only_admin_on_others
from mode import cleanup

from operator import itemgetter

from config import get_group_chat_id

logger = logging.getLogger(__name__)

QUARANTINE_MINUTES = 16 * 60
QUARANTIN_MUTE_DURATION = timedelta(hours=12)

DAILY_INFECTION_RATE = 0.01

COUGH_INFECTION_CHANCE_MASKED = 0.01
COUGH_INFECTION_CHANCE_UNMASKED = 0.3

RANDOM_COUGH_INFECTED_CHANCE = 0.99
RANDOM_COUGH_UNINFECTED_CHANCE = 0.002

INFECTION_CHANCE_MASKED = 0.01
INFECTION_CHANCE_UNMASKED = 0.15

LETHALITY_RATE = 0.8

JOB_QUEUE_DAILY_INFECTION_KEY = 'covid_daily_infection_job'
JOB_QUEUE_REPEATING_COUGHING_KEY = 'covid_repeating_coughing_job'

REPEATING_COUGHING_INTERVAL = timedelta(minutes=1)

DAILY_INFECTION_TIME = time(
    hour=0,
    minute=0,
    second=0,
    microsecond=0,
    tzinfo=None)


class DB:
    """
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
        self._setts: Collection = get_db(db_name).settings

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

    def get_covidstatus(self):
        setts = self._setts.find_one({})
        logger.debug(setts)
        if setts is None:
            return False
        return setts['covidstatus']

    def set_covidstatus(self, status):
        self._setts.update_one({}, {
            "$set": {"covidstatus": status}
        }, upsert=True)

    def infect(self, user_id: str):
        self._coll.update_one({"_id": user_id}, {
            "$set": {"infected_since": datetime.now()}
        })

    def is_user_infected(self, user_id: str):
        return self._coll.find_one({
            "_id": user_id,
            "infected_since": {"$exists": True}
        }) is not None

    def add_quarantine(self, user_id: str, since: datetime, until: datetime):
        self._coll.update_one({"_id": user_id}, {
            "$set": {
                "quarantined_since": since,
                "quarantined_until": until
            }
        })

    def get_quarantined(self):
        self._coll.find({"quarantined_until": {"$lte": datetime.now()}})

    def remove(self, user_id: str):
        self._coll.delete_one({"_id": user_id})

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name='covid')


def add_covid_mode(upd: Updater, handlers_group: int):
    logger.info("registering covid handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler(
            "cvstart",
            start,
            filters=admin_filter),
        handlers_group)
    dp.add_handler(
        CommandHandler(
            "cvstop",
            stop,
            filters=admin_filter),
        handlers_group)
    dp.add_handler(
        CommandHandler(
            "cvtest",
            test,
            filters=admin_filter),
        handlers_group)
    dp.add_handler(
        CommandHandler(
            "cvinfect",
            infect_admin,
            filters=admin_filter),
        handlers_group)
    dp.add_handler(CommandHandler("cough", cough), handlers_group)
    dp.add_handler(
        CommandHandler(
            "quarantine",
            quarantine,
            filters=admin_filter),
        handlers_group)
    dp.add_handler(
        CommandHandler(
            "temp",
            temp,
            filters=only_admin_on_others),
        handlers_group)

    # We must do this, since bot api doesnt present a way to get all members
    # of chat at once
    dp.add_handler(
        MessageHandler(
            Filters.all,
            callback=catch_message),
        handlers_group)

    if _db.get_covidstatus():
        set_handlers(dp.job_queue, dp.bot)


def set_handlers(queue: JobQueue, bot: Bot):
    logger.debug('Settings handlers')
    queue.run_daily(
        lambda _: daily_infection(
            get_group_chat_id(),
            bot),
        DAILY_INFECTION_TIME,
        name=JOB_QUEUE_DAILY_INFECTION_KEY)
    queue.run_repeating(
        lambda _: random_cough(bot, queue),
        REPEATING_COUGHING_INTERVAL,
        name=JOB_QUEUE_REPEATING_COUGHING_KEY)


@run_async
def stop(update: Update, context: CallbackContext):
    queue: JobQueue = context.job_queue

    try:
        covid_daily_infection_job, = queue.get_jobs_by_name(
            JOB_QUEUE_DAILY_INFECTION_KEY)

        if covid_daily_infection_job is not None:
            covid_daily_infection_job.schedule_removal()

        covid_repeating_coughing_job, = queue.get_jobs_by_name(
            JOB_QUEUE_REPEATING_COUGHING_KEY)

        if covid_repeating_coughing_job is not None:
            covid_repeating_coughing_job.schedule_removal()

        quarantined = _db.get_quarantined()

        if quarantined is not None:
            for user in quarantined:
                context.bot.restrict_chat_member(get_group_chat_id(), user["_id"],
                                                 can_add_web_page_previews=True,
                                                 can_send_media_messages=True,
                                                 can_send_other_messages=True,
                                                 can_send_messages=True)
        _db.remove_all()
    except Exception as err:
        logger.error(err)


@run_async
def start(update: Update, context: CallbackContext):
    stop(update, context)

    queue: JobQueue = context.job_queue

    set_handlers(queue, context.bot)

    _db.set_covidstatus(True)

    update.message.reply_text(f"ALARM!!! CORONAVIRUS IS SPREADING")


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
        context.bot.restrict_chat_member(update.effective_chat.id, user.id,
                                         until,
                                         can_add_web_page_previews=False,
                                         can_send_media_messages=False,
                                         can_send_other_messages=False,
                                         can_send_messages=False)
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
@cleanup(seconds=600)
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
            COUGH_INFECTION_CHANCE_UNMASKED)


@run_async
@cleanup(seconds=600)
def infect_admin(update: Update, context: CallbackContext):
    infect_user: User = update.message.reply_to_message.from_user
    _db.add(infect_user)
    _db.infect(infect_user.id)
    update.message.reply_text(
        f"{update.effective_user.full_name} опрокинул колбу с коронавирусом на {infect_user.full_name}")

@run_async
@cleanup(seconds=10)
def random_cough(bot: Bot, queue: JobQueue):
    users = _db.find_all()

    message = ''
    coughed_count = 0

    for _user in users:
        _rng = random()

        chance = .0

        if 'infected_since' in _user:
            chance = RANDOM_COUGH_INFECTED_CHANCE
        else:
            chance = RANDOM_COUGH_UNINFECTED_CHANCE

        full_name = _user['meta']['first_name']

        if 'last_name' in _user['meta']:
            full_name = f"{full_name} {_user['meta']['last_name']}"

        if _rng < chance:
            coughed_count = coughed_count + 1
            message = message + \
                (f"{full_name} чихнул в пространство") + "\n"

    if coughed_count > 0:
        bot.send_message(get_group_chat_id(), message)


def infect_user_masked_condition(
        user: User, masked_probability, unmasked_probability):
    if user is None:
        return

    _rng = random()

    photos: UserProfilePhotos = user.get_profile_photos()

    has_mask = False

    if photos.total_count > 0:
        photo: PhotoSize = sorted(photos[0], key=itemgetter('width'))[0]
        file_photo: File = photo.get_file()
        has_mask = is_avatar_has_mask(file_photo.download_as_bytearray())

        logger.debug(f"User {user.full_name} {has_mask}")

    infecting = False

    logger.debug(_rng)

    if has_mask:
        infecting = _rng <= masked_probability
    else:
        infecting = _rng <= unmasked_probability

    logger.debug(infecting)

    if infecting:
        logger.debug(f"User {user.full_name} infected")

        _db.infect(user.id)


prev_message_user: User = None


def catch_message(update: Update, context: CallbackContext):
    global prev_message_user
    user: User = update.effective_user

    if update.message is not None and update.message.reply_to_message is not None:
        _db.add(update.message.reply_to_message.from_user)

    user_to_infect: User = None

    if prev_message_user is not None:
        if _db.is_user_infected(user.id):
            user_to_infect = prev_message_user
        if _db.is_user_infected(prev_message_user.id):
            user_to_infect = user

    infect_user_masked_condition(
        user_to_infect,
        INFECTION_CHANCE_MASKED,
        INFECTION_CHANCE_UNMASKED)

    prev_message_user = user

    _db.add(user)

# @TODO


def hashImg(img: bytearray) -> str:
    sha1(img[-100:]).hexdigest()


def is_avatar_has_mask(img: bytearray, context: CallbackContext) -> Bool:
    if (img is None) or len(img) < 100:
        return False

    ## lookup existing value in cache
    hash = hashImg(img)
    isGood = context.chat_data['avatar_mask_cache'].get(hash)
    if isGood is not None:
        return isGood

    prediction_client = automl_v1beta1.PredictionServiceClient()

    name = 'projects/{}/locations/us-central1/models/{}'.format(
        config.get
        , model_id)
    payload = {'image': {'image_bytes': content}}
    params = {}
    request = prediction_client.predict(name, payload, params)
    return request.payload.display_name == "good"  # waits till request is returned


def daily_infection(chat_id, bot: Bot):
    members_count = bot.getChatMembersCount(chat_id)

    users = _db.find_all()

    infect_count = max(int(DAILY_INFECTION_RATE * members_count), 1)

    for _ in range(infect_count):
        infect_member = choice(users)

        _db.infect(infect_member["_id"])
