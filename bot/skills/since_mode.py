import logging
from datetime import datetime
from functools import reduce
from typing import Dict, List

# asyncio removed
from pymongo import MongoClient
from pymongo.collection import Collection
from telegram import Update  # Ensure Update is imported for type hints
from telegram.ext import Application, CallbackContext  # Add CallbackContext

from config import get_config
from mode import Mode
from handlers import ChatCommandHandler

conf = get_config()

client = MongoClient(f"mongodb://{conf['MONGO_USER']}:{conf['MONGO_PASS']}@mongo:27017")
topics_coll: Collection = client.since_mode.topics

logger = logging.getLogger(__name__)

mode = Mode(mode_name="since_mode", default=False, pin_info_msg=False)


@mode.add
def add_since_mode(application: Application, handlers_group: int):
    logger.info("register since-mode handlers")
    # In PTB v22+, Application is the dispatcher
    application.add_handler(
        ChatCommandHandler(
            "since",
            since_callback,
        ),
        handlers_group,
    )
    application.add_handler(
        ChatCommandHandler(
            "since_list",
            since_list_callback,
        ),
        handlers_group,
    )


def _get_topic(t: str) -> Dict:
    topic = topics_coll.find_one({"topic": t})
    logger.info("topic from db for title %s is %s", t, topic)

    return (
        topic
        if topic is not None
        else {"topic": t.lower(), "since_datetime": datetime.now(), "count": 1}
    )


def _get_delta_days(t: datetime) -> str:
    d = datetime.now() - t
    return f"{d.days}"


def _update_topic(t: Dict):
    if "_id" in t:
        topics_coll.update_one(
            {"topic": t["topic"]},
            {"$inc": {"count": 1}, "$set": {"since_datetime": datetime.now()}},
        )
    else:
        topics_coll.insert_one(t)


async def since_callback(update: Update, context: CallbackContext):
    """https://github.com/vldc-hq/vldc-bot/issues/11
    todo: normal doc, not this trash
    since scheme:
        {
            topic: "topic title",
            since_datetime: "datetime topic was last discussed",
            count: "how many times we discuss it"
        }

    """
    topic_title = " ".join(context.args)
    if len(topic_title) == 0:
        logging.warning("topic is empty")
        await update.message.reply_text("topic is empty 😿")
        return

    if len(topic_title) > 64:
        logging.warning("topic too long")
        await update.message.reply_text("topic too long 😿")
        return

    current_topic = _get_topic(topic_title)  # Remains sync
    await update.message.reply_text(
        f"{_get_delta_days(current_topic['since_datetime'])} days without «{current_topic['topic']}»! "
        f"Already was discussed {current_topic['count']} times\n",
    )

    _update_topic(current_topic)  # Remains sync


def _get_all_topics(limit: int) -> List[Dict]:
    return list(topics_coll.find({}).sort("-count").limit(limit))  # Remains sync


async def since_list_callback(
    update: Update, context: CallbackContext
):  # Added context
    # todo: need make it msg more pretty
    ts = reduce(
        lambda acc, el: acc
        + f"{_get_delta_days(el['since_datetime'])} days without «{el['topic']}»! "
        f"Already was discussed {el['count']} times\n",
        _get_all_topics(20),  # Remains sync
        "",
    )
    await update.message.reply_text(ts or "nothing yet 😿")
