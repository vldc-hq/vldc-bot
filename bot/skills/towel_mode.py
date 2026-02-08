import os
import logging
from datetime import datetime, timedelta
from random import choice
from typing import Dict, Any, Iterable, cast

import openai
from pymongo.collection import Collection
from telegram import Update, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

from config import get_config
from db.mongo import get_db
from handlers import ChatCommandHandler
from mode import Mode
from typing_utils import App, get_job_queue

MAGIC_NUMBER = "42"
QUARANTINE_TIME = 60
HELLO_MESSAGE_PIN_TIME = 48  # hours
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
OPENAI_ENABLED = bool(OPENAI_API_KEY)


# todo: extract maybe?
class DB:
    def __init__(self, db_name: str):
        self._coll: Collection[dict[str, Any]] = get_db(db_name).quarantine
        self._hello_messages: Collection[dict[str, Any]] = get_db(
            db_name
        ).hello_messages

    def add_user(self, user_id: int):
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

    def find_user(self, user_id: int) -> Dict[str, Any] | None:
        return self._coll.find_one({"_id": user_id})

    def find_all_users(self) -> Iterable[Dict[str, Any]]:
        return self._coll.find({})

    def add_user_rel_message(self, user_id: int, message_id: int):
        self._coll.update_one(
            {"_id": user_id}, {"$addToSet": {"rel_messages": message_id}}
        )

    def delete_user(self, user_id: int):
        return self._coll.delete_one({"_id": user_id})

    def delete_all_users(self):
        return self._coll.delete_many({})

    def save_hello_message(
        self, user_id: int, username: str, message_text: str, message_id: int
    ):
        """Save user's hello message for 48 hours"""
        self._hello_messages.insert_one(
            {
                "user_id": user_id,
                "username": username,
                "message_text": message_text,
                "message_id": message_id,
                "timestamp": datetime.now(),
                "expires_at": datetime.now() + timedelta(hours=48),
            }
        )

    def get_hello_message(self, user_id: int) -> Dict[str, Any] | None:
        """Get user's hello message if it exists and hasn't expired"""
        return self._hello_messages.find_one(
            {
                "user_id": user_id,
                "expires_at": {"$gt": datetime.now()},
            }
        )


db = DB("towel_mode")


def _clear_quarantine(_: App) -> None:
    db.delete_all_users()


mode = Mode(mode_name="towel_mode", default=True, off_callback=_clear_quarantine)


def _is_time_gone(user: Dict[str, Any]) -> bool:
    return user["datetime"] < datetime.now()


async def _delete_user_rel_messages(
    chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE
):
    user = db.find_user(user_id=user_id)
    if user is None:
        return
    for msg_id in user["rel_messages"]:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except BadRequest as err:
            logger.info("can't delete msg: %s", err)


async def _unpin_message_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job to unpin a message after 48 hours"""
    if context.job is None or context.job.data is None:
        return
    chat_id = context.job.data.get("chat_id")
    message_id = context.job.data.get("message_id")
    if chat_id is None or message_id is None:
        return
    try:
        await context.bot.unpin_chat_message(chat_id, message_id)
        logger.info("unpinned message %d in chat %d", message_id, chat_id)
    except BadRequest as err:
        logger.info("can't unpin message: %s", err)


async def _pin_hello_message(
    chat_id: int, message_id: int, username: str, context: ContextTypes.DEFAULT_TYPE
):
    """Pin a hello message for 48 hours"""
    try:
        await context.bot.pin_chat_message(
            chat_id, message_id, disable_notification=True
        )
        logger.info("pinned hello message %d for user %s", message_id, username)

        # Schedule unpinning after 48 hours
        job_queue = get_job_queue(context)
        if job_queue is not None:
            job_queue.run_once(
                _unpin_message_job,
                timedelta(hours=HELLO_MESSAGE_PIN_TIME),
                data={"chat_id": chat_id, "message_id": message_id},
            )
    except BadRequest as err:
        logger.warning("can't pin message: %s", err)


@mode.add
def add_towel_mode(app: App, handlers_group: int):
    logger.info("registering towel-mode handlers")

    # catch all new users and drop the towel
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS, catch_new_user, block=False
        ),
        group=handlers_group,
    )

    # check for reply or remove messages
    app.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.StatusUpdate.ALL,
            catch_reply,
            block=False,
        ),
        group=handlers_group,
    )

    # "i am a bot button"
    app.add_handler(
        CallbackQueryHandler(i_am_a_bot_btn, block=False), group=handlers_group
    )

    # ban quarantine users, if time is gone
    group_chat_id = get_config()["GROUP_CHAT_ID"]
    if group_chat_id and app.job_queue is not None:
        app.job_queue.run_repeating(
            ban_user,
            interval=60,
            first=60,
            data={"chat_id": group_chat_id},
        )
    else:
        logger.warning("CHAT_ID is empty; towel_mode ban job is disabled")

    # admin command to view saved hello messages
    app.add_handler(
        ChatCommandHandler(
            "hellomsg",
            view_hello_message,
            require_admin=True,
        ),
        group=handlers_group,
    )


async def quarantine_user(user: User, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    logger.info("put %s in quarantine", user)
    db.add_user(user.id)

    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(choice(I_AM_BOT), callback_data=MAGIC_NUMBER)]]
    )

    message_id = (
        await context.bot.send_message(
            chat_id,
            f"{user.name} НЕ нажимай на кнопку ниже, чтобы доказать, что ты не бот.\n"
            "Просто ответь (reply) на это сообщение, кратко написав о себе (у нас так принято).\n"
            "Я буду удалять твои сообщения, пока ты не сделаешь это.\n"
            f"А коли не сделаешь, через {QUARANTINE_TIME} минут выкину из чата.\n"
            "Ничего личного, просто боты одолели.\n",
            reply_markup=markup,
        )
    ).message_id

    # messages from `rel_message` will be deleted after greeting or ban
    db.add_user_rel_message(
        user.id,
        message_id,
    )

    bot_user = await context.bot.get_me()
    if user.id == bot_user.id:
        message_id = (
            await context.bot.send_message(
                chat_id,
                "Я простой бот из Владивостока.\n"
                "В-основном занимаюсь тем, что бросаю полотенца в новичков.\n"
                "Увлекаюсь переписыванием себя на раст, но на это постоянно не хватает времени.\n",
                reply_to_message_id=message_id,
            )
        ).message_id

        db.delete_user(user_id=user.id)
        await context.bot.send_message(
            chat_id, "Добро пожаловать в VLDC!", reply_to_message_id=message_id
        )


async def catch_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.effective_chat is None:
        return
    for user in update.message.new_chat_members:
        await quarantine_user(user, update.effective_chat.id, context)


async def catch_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # todo: cache it
    if update.effective_user is None:
        return
    if update.effective_message is None:
        return
    if update.effective_chat is None:
        return
    user_id = update.effective_user.id
    user = db.find_user(user_id)
    if user is None:
        return

    # Check if the message is a reply to the bot
    if (
        update.effective_message.reply_to_message is not None
        and update.effective_message.reply_to_message.from_user is not None
        and update.effective_message.reply_to_message.from_user.id
        == (await context.bot.get_me()).id
    ):
        # Check reply length
        text = update.effective_message.text or ""
        if len(text) < 15:
            # Delete the short reply
            await context.bot.delete_message(
                update.effective_chat.id, update.effective_message.message_id
            )
            # Send feedback message
            feedback_msg = await context.bot.send_message(
                update.effective_chat.id,
                f"{update.effective_user.name}, твой ответ слишком короткий. "
                "Я верю, что ты можешь написать больше о себе!",
            )
            # Add feedback message to related messages for cleanup
            db.add_user_rel_message(user_id, feedback_msg.message_id)
        elif is_worthy(text):
            # Valid reply - welcome the user
            await _delete_user_rel_messages(update.effective_chat.id, user_id, context)
            db.delete_user(user_id=cast(int, user["_id"]))
            if update.message is not None:
                # Save hello message to database
                db.save_hello_message(
                    user_id=user_id,
                    username=update.effective_user.name or str(user_id),
                    message_text=text,
                    message_id=update.effective_message.message_id,
                )

                # Pin the hello message for 48 hours
                await _pin_hello_message(
                    update.effective_chat.id,
                    update.effective_message.message_id,
                    update.effective_user.name or str(user_id),
                    context,
                )

                await update.message.reply_text("Добро пожаловать в VLDC!")
        else:
            # Reply doesn't pass OpenAI check - delete it
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.effective_message.message_id,
            )
    else:
        # Not a reply to bot - delete it
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
        )


def is_worthy(text: str) -> bool:
    """check if reply is a valid bio as requested"""
    if not OPENAI_ENABLED:
        logger.info("openai disabled; skipping spam check")
        return True

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

    try:
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
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("openai spam check failed: %s", exc)
        return True

    verdict = response.choices[0].message.content
    logger.info("text: %s is %s", text, verdict)

    return verdict != "spam"


async def quarantine_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user is None:
        return
    if update.effective_message is None:
        return
    if update.effective_chat is None:
        return
    user_id = update.effective_user.id
    # todo: cache it
    user = db.find_user(user_id)
    # if user exist -> remove message
    if user is not None:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.effective_message.message_id,
        )


async def i_am_a_bot_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = update.callback_query
    if user is None or query is None:
        return

    if query.data == MAGIC_NUMBER:
        if db.find_user(user.id) is not None:
            msg = f"{user.name}, попробуй прочитать сообщение от бота внимательней :3"
        else:
            msg = f"Любопытство сгубило кошку, {user.name} :3"

        await context.bot.answer_callback_query(query.id, msg, show_alert=True)


async def ban_user(context: ContextTypes.DEFAULT_TYPE):
    # fixme: smth wrong here
    if context.job is None:
        logger.warning("job is missing; skipping ban_user job")
        return
    job_data = context.job.data
    if not isinstance(job_data, dict):
        logger.warning("job data missing or invalid; skipping ban_user job")
        return
    job_data = cast(dict[str, Any], job_data)
    group_chat_id = job_data.get("chat_id")
    if not isinstance(group_chat_id, (int, str)):
        logger.warning("CHAT_ID has invalid type; skipping ban_user job")
        return
    if not group_chat_id:
        logger.warning("CHAT_ID is empty; skipping ban_user job")
        return

    chat_id = (await context.bot.get_chat(chat_id=group_chat_id)).id
    logger.debug("get chat.id: %s", chat_id)

    for user in db.find_all_users():
        if _is_time_gone(user):
            user_id = int(user["_id"])
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await _delete_user_rel_messages(chat_id, user_id, context)
            except BadRequest as err:
                logger.error("can't ban user %s, because of: %s", user, err)
                continue

            db.delete_user(user_id)

            logger.info("user banned: %s", user)


async def view_hello_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view a user's saved hello message"""
    if update.message is None:
        return

    # Check if command is a reply to a message
    if update.message.reply_to_message is None:
        await update.message.reply_text(
            "Используй эту команду как ответ (reply) на сообщение пользователя."
        )
        return

    target_user = update.message.reply_to_message.from_user
    if target_user is None:
        await update.message.reply_text("Не могу определить пользователя.")
        return

    # Get the saved hello message from database
    hello_msg = db.get_hello_message(target_user.id)

    if hello_msg is None:
        await update.message.reply_text(
            f"Не найдено сохранённое приветственное сообщение для {target_user.name}.\n"
            "Возможно, оно было отправлено более 48 часов назад или пользователь ещё не прошёл карантин."
        )
        return

    # Format the response
    timestamp = hello_msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    expires_at = hello_msg["expires_at"].strftime("%Y-%m-%d %H:%M:%S")
    response = (
        f"📝 Приветственное сообщение от {hello_msg['username']}:\n"
        f"Отправлено: {timestamp}\n"
        f"Истекает: {expires_at}\n\n"
        f"Текст:\n{hello_msg['message_text']}"
    )

    await update.message.reply_text(response)
