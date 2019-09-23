import logging
from datetime import datetime
from functools import reduce
from typing import Dict, List

from pymongo import MongoClient
from pymongo.collection import Collection
from telegram.ext import Updater, CommandHandler

from config import get_config

conf = get_config()

client = MongoClient(f"mongodb://{conf['MONGO_USER']}:{conf['MONGO_PASS']}@mongo:27017")
topics_coll: Collection = client.since_mode.topics

logger = logging.getLogger(__name__)


def add_since_mode_handlers(upd: Updater, since_mode_handlers_group: int):
    logger.info("register since-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("since", since_callback), since_mode_handlers_group)
    dp.add_handler(CommandHandler("since_list", since_list_callback), since_mode_handlers_group)


def _get_topic(t: str) -> Dict:
    topic = topics_coll.find_one({"topic": t})
    logger.info(f"topic from db for title {t} is {topic}")

    return topic if topic is not None else {
        "topic": t.lower(),
        "since_datetime": datetime.now(),
        "count": 1
    }


def _get_delta(t: datetime) -> str:
    # todo: replace it with pretty natural time
    d = datetime.now() - t
    return f"{d.seconds}"


def _update_topic(t: Dict):
    if "_id" in t:
        topics_coll.update_one(
            {"topic": t["topic"]},
            {
                "$inc": {'count': 1},
                "$set": {'since_datetime': datetime.now()}
            }
        )
    else:
        topics_coll.insert_one(t)


def since_callback(update, context):
    """  https://github.com/egregors/vldc-bot/issues/11
    todo: normal doc, not this trash
    since scheme:
        {
            topic: "topic title",
            since: "datetime topic was last discussed",
            count: "how many times we discuss it"
        }

     """
    topic_title = " ".join(context.args)
    if len(topic_title) == 0:
        logging.warning(f"topic is empty")
        return

    current_topic = _get_topic(topic_title)
    update.message.reply_text(
        f"«{current_topic['topic']}» was last discussed {_get_delta(current_topic['since_datetime'])} seconds ago. "
        f"This is {current_topic['count']}th mention of this topic"
    )

    _update_topic(current_topic)


def _get_all_topics(limit: int) -> List[Dict]:
    return list(topics_coll.find({}).sort("-count").limit(limit))


def since_list_callback(update, context):
    # todo: need make it msg more pretty
    ts = reduce(
        lambda acc, el: acc + f"{el['topic']}: "
                              f"was last discussed {_get_delta(el['since_datetime'])} secs ago "
                              f"{el['count']} times \n",
        _get_all_topics(20),
        ""
    )
    update.message.reply_text(ts or "nothing yet 😿")
