import logging
from datetime import datetime

from pymongo import MongoClient
from pymongo.collection import Collection
from telegram.ext import Updater, CommandHandler

from config import get_config

conf = get_config()

client = MongoClient(f"mongodb://{conf['MONGO_USER']}:{conf['MONGO_PASS']}@mongo:27017")
db = client.since_mode

logger = logging.getLogger(__name__)


def add_since_mode_handlers(upd: Updater, since_mode_handlers_group: int):
    logger.info("register since-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("since", since_callback), since_mode_handlers_group)


def since_callback(update, context):
    topic = " ".join(context.args)
    coll: Collection = db.topics
    t = coll.find_one({'topic': topic})
    logger.info(t)

    if t:
        coll.update_one(
            {"topic": topic.lower()},
            {
                "$inc": {'count': 1},
                "$set": {'since_datetime': datetime.now()}
            }
        )
    else:
        t = {
            "topic": topic.lower(),
            "since_datetime": datetime.now(),
            "count": 1
        }
        coll.insert_one(t)

    delta = datetime.now() - t['since_datetime']

    update.message.reply_text(
        f"This is are {delta.seconds} seconds since «{t['topic']}» discussion\n"
        f"This is are {t['count']} time we are talking about «{t['topic']}»"
    )
