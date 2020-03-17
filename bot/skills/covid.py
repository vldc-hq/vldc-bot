import logging
from datetime import datetime, timedelta, time
from random import choice, random
from threading import Lock
from typing import List, Tuple, Dict

import pymongo
import telegram
from pymongo.collection import Collection
from telegram import Update, User, Bot, Message, UserProfilePhotos, File, PhotoSize
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async, JobQueue, MessageHandler, Job

from db.mongo import get_db
from filters import admin_filter, only_admin_on_others
from mode import cleanup

from config import get_group_chat_id

logger = logging.getLogger(__name__)

QUARANTINE_MINUTES = 16 * 60
QUARANTIN_MUTE_DURATION = timedelta(hours=12)

DAILY_INFECTION_RATE = 0.01

COUGH_INFECTION_CHANCE_MASKED = 0.01
COUGH_INFECTION_CHANCE_UNMASKED = 0.3

RANDOM_COUGH_INFECTED_CHANCE = 0.1
RANDOM_COUGH_UNINFECTED_CHANCE = 0.002

INFECTION_CHANCE_MASKED = 0.01
INFECTION_CHANCE_UNMASKED = 0.15

LETHALITY_RATE = 0.8

JOB_QUEUE_DAILY_INFECTION_KEY = 'covid_daily_infection_job'
JOB_QUEUE_REPEATING_COUGHING_KEY = 'covid_repeating_coughing_job'

REPEATING_COUGHING_INTERVAL = timedelta(minutes=1)

DAILY_INFECTION_TIME = time(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

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
    """

    def __init__(self, db_name: str):
        self._members: Collection = get_db(db_name).members

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

    def is_user_infected(self, user_id: str):
        return self._coll.find_one({
            "_id": user_id, 
            "infected_since": { "$exists": False }
        }) != None

    def add_quarantine(self, user_id: str, since: datetime, until: datetime):
        self._coll.update_one({"_id": user_id}, {
            "$set": {
                "quarantined_since": since,
                "quarantined_until": until
            }
        })

    def get_quarantined(self):
        self._coll.find({ "quarantined_until": { "$lte": datetime.now() } })

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

_db = DB(db_name='covid')

def add_covid(upd: Updater, handlers_group: int):
    logger.info("registering covid handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("cvstart", start, filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler("cvstop", stop, filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler("cvtest", test, filters=admin_filter), handlers_group)
    dp.add_handler(CommandHandler("cough", cough), handlers_group)
    dp.add_handler(CommandHandler("temp", show_hussars, filters=only_admin_on_others), handlers_group)

    # We must do this, since bot api doesnt present a way to get all members of chat at once
    dp.add_handler(MessageHandler(callback=catch_message), handlers_group)

@run_async
def stop(update: Update, context: CallbackContext):
    queue: JobQueue = context.job_queue

    covid_daily_infection_job: Job = queue.get_jobs_by_name(JOB_QUEUE_DAILY_INFECTION_KEY)

    if covid_daily_infection_job != None:
        covid_daily_infection_job.schedule_removal()

    covid_repeating_coughing_job: Job = queue.get_jobs_by_name(JOB_QUEUE_REPEATING_COUGHING_KEY)

    if covid_repeating_coughing_job != None:
        covid_repeating_coughing_job.schedule_removal()

    quarantined = _db.get_quarantined()

    for user in quarantined:
        context.bot.restrict_chat_member(get_group_chat_id(), user["_id"],
                                         can_add_web_page_previews=True,
                                         can_send_media_messages=True,
                                         can_send_other_messages=True,
                                         can_send_messages=True)

    _db.remove_all()

@run_async
def start(update: Update, context: CallbackContext):
    stop(update, context)

    queue: JobQueue = context.job_queue

    queue.run_daily(daily_infection, DAILY_INFECTION_TIME, name=JOB_QUEUE_DAILY_INFECTION_KEY)
    queue.run_repeating(lambda _: random_cough(context), REPEATING_COUGHING_INTERVAL, name=JOB_QUEUE_REPEATING_COUGHING_KEY)

    update.message.reply_text(f"ALARM!!! CORONAVIRUS IS SPREADING")

@run_async
def temp(update: Update, context: CallbackContext):
    message: Message = update.message
    user: User = message.from_user

    if message.reply_to_message:
        user = message.reply_to_message.user

    mdb_user = _db.find(user.id)

    temp_appendix = 0

    if mdb_user != None:
        if 'infected_since' in mdb_user:
            days_count = (datetime.now() - mdb_user['infected_since']).days
            temp_appendix = random() * max(days_count / 4)
    
    if temp_appendix == 0:
        temp_appendix = random() + 1.5 * random()

    temp = 36 + temp_appendix

    message.reply_text(f"У {user.full_name} температура {temp} С")

@run_async
def quarantine(update: Update, context: CallbackContext):
    try:
        user: User = update.message.reply_to_message.from_user
        update.message.reply_text(f"{user.full_name} помещён в карантин на {QUARANTIN_MUTE_DURATION}")
        since = datetime.now()
        until = since + QUARANTIN_MUTE_DURATION
        _db.add_quarantine(user.id, since, until)
        context.bot.restrict_chat_member(update.effective_chat.id, user.id,
                                         until,
                                         can_add_web_page_previews=False,
                                         can_send_media_messages=False,
                                         can_send_other_messages=True,
                                         can_send_messages=False)

@run_async
def test(update: Update, context: CallbackContext):
    try:
        reply_user: User = update.message.reply_to_message.from_user

        if _db.is_user_infected(reply_user):
            update.message.reply_text(f"😿 {reply_user.full_name} инфицирован")
        else:
            update.message.reply_text(f"{reply_user.full_name} здоров")
    except Exception as err:
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")

@run_async
@cleanup(seconds=600)
def cough(update: Update, context: CallbackContext):
    user: User = update.effective_user

    if update.message.reply_to_message == None:
        update.message.reply_text(f"{user.full_name} чихнул в пространство")
        return

    reply_user: User = update.message.reply_to_message.from_user

    update.message.reply_text(f"{reply_user.full_name} чихнул на")
    infect_user_masked_condition(reply_user, COUGH_INFECTION_CHANCE_MASKED, COUGH_INFECTION_CHANCE_UNMASKED)

@run_async
@cleanup(seconds=600)
def random_cough(context: CallbackContext):
    users = _db.find_all()

    message = ''
    coughed_count = 0

    for _user in users:
        _rng = random()

        chance = 0

        if 'infected_since' in _user:
            chance = RANDOM_COUGH_INFECTED_CHANCE
        else:
            chance = RANDOM_COUGH_UNINFECTED_CHANCE

        if _rng < chance:
            coughed_count = coughed_count + 1
            message = message + (f"{_user['meta']['full_name']} чихнул в пространство") + "\n"
    
    if coughed_count > 0:
        context.bot.send_message(get_group_chat_id(), message)

def infect_user_masked_condition(user: User, masked_probability, unmasked_probability):
    _rng = random()

    photos: UserProfilePhotos = user.get_profile_photos()

    has_mask = False

    if photos.total_count > 0:
        photo: PhotoSize = max(photo.width for photo in photos[0])
        file_photo: File = photo.get_file()
        has_mask = is_avatar_has_mask(file_photo.download_as_bytearray())
    
    infecting = False

    if has_mask:
        infecting = _rng < masked_probability
    else:
        infecting = _rng < unmasked_probability
    
    if infecting:
        _db.infect(user)

prev_message_user: User = None
def catch_message(update: Update, context: CallbackContext):
    user: User = update.effective_user

    user_to_infect: User = None

    if _db.is_user_infected(user.id):
        user_to_infect = prev_message_user
    if _db.is_user_infected(prev_message_user.id):
        user_to_infect = user

    infect_user_masked_condition(user_to_infect, INFECTION_CHANCE_MASKED, INFECTION_CHANCE_UNMASKED) 

    prev_message_user = user

    _db.add(user)

# @TODO
def is_avatar_has_mask(img: bytearray):
    return False

def daily_infection(chat_id, bot: Bot):
    members_count = bot.getChatMembersCount(chat_id)

    users = _db.find_all

    infect_count = min(int(DAILY_INFECTION_RATE * members_count), 1)

    for _ in range(infect_count):
        infect_member = choice(users)

        _db.infect(infect_member["_id"])