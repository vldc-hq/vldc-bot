import logging
from datetime import datetime, timedelta
from random import choice
from typing import Dict

from pymongo.collection import Collection
from telegram import Update, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, run_async, CallbackQueryHandler, \
    CommandHandler

from config import get_config
from db.mongo import get_db
from mode import Mode

MAGIC_NUMBER = "42"
QUARANTINE_TIME = 60
I_AM_BOT = [
    "I am a bot!",
    "Я бот!",
    "私はボットです！",
    "Ma olen bot!",
    "मैं एक बॉट हूँ!",
    "Je suis un bot!",
    "Unë jam një bot!",
    "أنا بوت!",
    "אני בוט!",
    "Sono un robot!",
    "我是機器人！"
]

logger = logging.getLogger(__name__)


# todo: extract maybe?
class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).quarantine

    def add_user(self, user_id: str):
        return self._coll.insert_one({
            "_id": user_id,
            "rel_messages": [],
            "datetime": datetime.now() + timedelta(minutes=QUARANTINE_TIME)
        }) if self.find_user(user_id) is None else None

    def find_user(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def find_all_users(self):
        return self._coll.find({})

    def add_user_rel_message(self, user_id: str, message_id: str):
        self._coll.update_one({"_id": user_id}, {"$addToSet": {"rel_messages": message_id}})

    def delete_user(self, user_id: str):
        return self._coll.delete_one({"_id": user_id})


db = DB("towel_mode")
mode = Mode(mode_name="towel_mode", default=True)


@mode.add
def add_towel_mode(upd: Updater, handlers_group: int):
    logger.info("registering towel-mode handlers")
    dp = upd.dispatcher

    # catch all new users and drop the towel
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, catch_new_user),
                   handlers_group)

    # check for reply or remove messages
    dp.add_handler(MessageHandler(
        Filters.group & ~Filters.status_update, catch_reply),
        handlers_group
    )

    # "i am a bot button"
    dp.add_handler(CallbackQueryHandler(i_am_a_bot_btn), handlers_group)

    # ban quarantine users, if time is gone
    upd.job_queue.run_repeating(ban_user, interval=60, first=60, context={
        "chat_id": get_config()["GROUP_CHAT_ID"]
    })


@run_async
def quarantine_user(user: User, chat_id: str, context: CallbackContext):
    logger.info(f"put {user} in quarantine")
    db.add_user(user.id)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(choice(I_AM_BOT), callback_data=MAGIC_NUMBER)]])

    # messages from `rel_message` will be deleted after greeting or ban
    db.add_user_rel_message(user.id, context.bot.send_message(
        chat_id,
        f"{user.name} НЕ нажимай на кнопку ниже, чтобы доказать, что ты не бот.\n"
        "Просто ответь (reply) на это сообщение, кратко написав о себе (у нас так принято).\n"
        "Я буду удалять твои сообщения, пока ты не сделаешь это.\n"
        f"А коли не сделаешь, через {QUARANTINE_TIME} минут выкину из чата.\n"
        "Ничего личного, просто боты одолели.\n",
        reply_markup=markup
    ).message_id)


@run_async
def catch_new_user(update: Update, context: CallbackContext):
    for user in update.message.new_chat_members:
        quarantine_user(user, update.effective_chat.id, context)


@run_async
def catch_reply(update: Update, context: CallbackContext):
    # todo: cache it
    user_id = update.effective_user.id
    user = db.find_user(user_id)
    if user is None:
        return

    if update.effective_message.reply_to_message is not None and \
            update.effective_message.reply_to_message.from_user.id == context.bot.get_me().id:

        for msg_id in db.find_user(user_id=user["_id"])["rel_messages"]:
            context.bot.delete_message(update.effective_chat.id, msg_id)

        db.delete_user(user_id=user["_id"])
        update.message.reply_text("Добро пожаловать в VLDC!")
    else:
        context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id, 10
        )


@run_async
def quarantine_filter(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # todo: cache it
    user = db.find_user(user_id)
    # if user exist -> remove message
    if user is not None:
        context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id, 10
        )


@run_async
def i_am_a_bot_btn(update: Update, context: CallbackContext):
    user = update.effective_user
    query = update.callback_query

    if query.data == MAGIC_NUMBER and db.find_user(user.id) is not None:
        context.bot.answer_callback_query(
            query.id,
            f"{user.name}, попробуй прочитать сообщение от бота внимательней :3",
            show_alert=True
        )


def _is_time_gone(user: Dict) -> bool:
    return user["datetime"] < datetime.now()


@run_async
def ban_user(context: CallbackContext):
    chat_id = context.bot.get_chat(chat_id=context.job.context["chat_id"]).id
    logger.debug(f"get chat.id: {chat_id}")

    # sorry about that
    chat_data = context._dispatcher.chat_data.get(chat_id)  # noqa
    if chat_data is not None:
        for user in db.find_all_users():
            if _is_time_gone(user):
                context.bot.kick_chat_member(chat_id, user['_id'])
                db.delete_user(user['_id'])
                logger.debug(f"user banned: {user['_id']}")
