import os
import logging
from datetime import datetime, timedelta
from random import choice
from typing import Dict

import openai
from pymongo.collection import Collection

# asyncio removed
from telegram import Update, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
)

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
    "我是機器人！",
]

logger = logging.getLogger(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


# todo: extract maybe?
class DB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).quarantine

    def add_user(self, user_id: str):
        return (
            self._coll.insert_one(
                {
                    "_id": user_id,
                    "rel_messages": [],
                    "datetime": datetime.now() + timedelta(minutes=QUARANTINE_TIME),
                }
            )
            if self.find_user(user_id) is None
            else None
        )

    def find_user(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def find_all_users(self):
        return self._coll.find({})

    def add_user_rel_message(self, user_id: str, message_id: str):
        self._coll.update_one(
            {"_id": user_id}, {"$addToSet": {"rel_messages": message_id}}
        )

    def delete_user(self, user_id: str):
        return self._coll.delete_one({"_id": user_id})

    def delete_all_users(self):
        return self._coll.delete_many({})


db = DB("towel_mode")
mode = Mode(
    mode_name="towel_mode", default=True, off_callback=lambda _: db.delete_all_users()
)


def _is_time_gone(user: Dict) -> bool:
    return user["datetime"] < datetime.now()


async def _delete_user_rel_messages(
    chat_id: int, user_id: str, context: CallbackContext
):
    # Assuming db.find_user remains synchronous for now
    user_data = db.find_user(user_id=user_id)
    if user_data and "rel_messages" in user_data:
        for msg_id in user_data["rel_messages"]:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except BadRequest as err:
                logger.info("can't delete msg: %s", err)


@mode.add
def add_towel_mode(application: Application, handlers_group: int):
    logger.info("registering towel-mode handlers")
    # application object itself is the dispatcher in PTB v22+

    # catch all new users and drop the towel
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, catch_new_user),
        handlers_group,
    )

    # check for reply or remove messages
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS
            & ~filters.StatusUpdate.ALL,  # Assuming GROUPS is the intended filter
            catch_reply,
        ),
        handlers_group,
    )

    # "i am a bot button"
    application.add_handler(CallbackQueryHandler(i_am_a_bot_btn), handlers_group)

    # ban quarantine users, if time is gone
    application.job_queue.run_repeating(  # Changed upd.job_queue to application.job_queue
        ban_user,  # ban_user will be made async
        interval=60,
        first=60,
        context={"chat_id": get_config()["GROUP_CHAT_ID"]},
    )


async def quarantine_user(user: User, chat_id: str, context: CallbackContext):
    logger.info("put %s in quarantine", user)
    db.add_user(user.id)  # DB op remains sync

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(choice(I_AM_BOT), callback_data=MAGIC_NUMBER)]]
    )

    message_id_obj = await context.bot.send_message(
        chat_id,
        f"{user.name} НЕ нажимай на кнопку ниже, чтобы доказать, что ты не бот.\n"
        "Просто ответь (reply) на это сообщение, кратко написав о себе (у нас так принято).\n"
        "Я буду удалять твои сообщения, пока ты не сделаешь это.\n"
        f"А коли не сделаешь, через {QUARANTINE_TIME} минут выкину из чата.\n"
        "Ничего личного, просто боты одолели.\n",
        reply_markup=markup,
    )
    message_id = message_id_obj.message_id

    # messages from `rel_message` will be deleted after greeting or ban
    # DB op remains sync
    db.add_user_rel_message(
        user.id,
        message_id,
    )

    me_user = await context.bot.get_me()
    if user.id == me_user.id:
        vldc_greeting_message_obj = await context.bot.send_message(
            chat_id,
            "Я простой бот из Владивостока.\n"
            "В-основном занимаюсь тем, что бросаю полотенца в новичков.\n"
            "Увлекаюсь переписыванием себя на раст, но на это постоянно не хватает времени.\n",
            reply_to_message_id=message_id,  # Replying to the original quarantine message
        )
        # message_id_vldc = vldc_greeting_message_obj.message_id # New message_id if needed later

        db.delete_user(user_id=user.id)  # This is the line black struggles with

        await context.bot.send_message(
            chat_id,
            "Добро пожаловать в VLDC!",
            reply_to_message_id=vldc_greeting_message_obj.message_id,  # Replying to the bot's own previous message
        )


async def catch_new_user(update: Update, context: CallbackContext):
    for (
        user_obj
    ) in update.message.new_chat_members:  # Renamed user to user_obj to avoid conflict
        await quarantine_user(user_obj, update.effective_chat.id, context)


async def catch_reply(update: Update, context: CallbackContext):
    # todo: cache it
    user_id = update.effective_user.id
    user = db.find_user(user_id)  # DB op remains sync
    if user is None:
        return

    if (
        update.effective_message.reply_to_message is not None
        and update.effective_message.reply_to_message.from_user.id
        == (await context.bot.get_me()).id  # await get_me()
        and is_worthy(update.effective_message.text)  # is_worthy remains sync
    ):
        await _delete_user_rel_messages(update.effective_chat.id, user_id, context)
        db.delete_user(user_id=user["_id"])  # DB op remains sync

        await update.message.reply_text("Добро пожаловать в VLDC!")
    else:
        await context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id, 10
        )


def is_worthy(text: str) -> bool:  # is_worthy and its OpenAI call remain sync
    """check if reply is a valid bio as requested"""

    # backdoor for testing
    if text.lower().find("i love vldc") != -1:
        return True

    if len(text) < 15:
        return False

    prompt = """You are a spam-fighting bot, guarding chat room from bad actors and advertisement.
All users entering the chat are required to reply to the bot's message with a short bio.
Sometimes bots can be tricky and answer with bio that is also a spam.
For example: "я инвестор со стажем, могу дать информацию, ищу партнеров" is a spam.
Next message is the first message of the user in the chat. Can it be considered as a short bio?
Answer with a single word: spam or legit."""

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        temperature=0.9,
        max_tokens=150,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.6,
    )

    logger.info("text: %s is %s", text, response.choices[0].message.content)

    return response.choices[0].message.content != "spam"


def quarantine_filter(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    # todo: cache it
    user = db.find_user(user_id)
    # if user exist -> remove message
    if user is not None:
        context.bot.delete_message(
            update.effective_chat.id, update.effective_message.message_id, 10
        )


async def i_am_a_bot_btn(update: Update, context: CallbackContext):
    user = update.effective_user
    query = update.callback_query

    if query.data == MAGIC_NUMBER:
        if db.find_user(user.id) is not None:  # DB op remains sync
            msg = f"{user.name}, попробуй прочитать сообщение от бота внимательней :3"
        else:
            msg = f"Любопытство сгубило кошку, {user.name} :3"

        await context.bot.answer_callback_query(query.id, msg, show_alert=True)


async def ban_user(context: CallbackContext):
    # fixme: smth wrong here
    chat = await context.bot.get_chat(
        chat_id=context.job.data["chat_id"]
    )  # context.job.context to context.job.data
    chat_id = chat.id
    logger.debug("get chat.id: %s", chat_id)

    for (
        user_data
    ) in db.find_all_users():  # DB op remains sync, renamed user to user_data
        if _is_time_gone(user_data):  # _is_time_gone remains sync
            try:
                await context.bot.kick_chat_member(chat_id, user_data["_id"])
                await _delete_user_rel_messages(chat_id, user_data["_id"], context)
            except BadRequest as err:
                logger.error("can't ban user %s, because of: %s", user_data, err)
                continue

            db.delete_user(user_data["_id"])  # DB op remains sync

            logger.info("user banned: %s", user_data)
