import os
import logging
from datetime import datetime
from random import choice
from typing import Dict, Any, cast

import openai
from telegram import Update, User, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import BadRequest
from telegram.ext import (
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)

from config import get_config
from db.sqlite import db as sqlite_db
from mode import Mode
from typing_utils import App

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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
OPENAI_ENABLED = bool(OPENAI_API_KEY)


def _clear_quarantine(_: App) -> None:
    sqlite_db.delete_all_quarantine_users()


mode = Mode(mode_name="towel_mode", default=True, off_callback=_clear_quarantine)


def _is_time_gone(user: Dict[str, Any]) -> bool:
    return user["datetime"] < datetime.now()


async def _delete_user_rel_messages(
    chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE
):
    user = sqlite_db.find_quarantine_user(user_id=user_id)
    if user is None:
        return
    for msg_id in user["rel_messages"]:
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except BadRequest as err:
            logger.info("can't delete msg: %s", err)


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


async def quarantine_user(user: User, chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    logger.info("put %s in quarantine", user)
    sqlite_db.add_quarantine_user(user.id, QUARANTINE_TIME)

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
    sqlite_db.add_quarantine_rel_message(
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

        sqlite_db.delete_quarantine_user(user_id=user.id)
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
    user = sqlite_db.find_quarantine_user(user_id)
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
            sqlite_db.add_quarantine_rel_message(user_id, feedback_msg.message_id)
        elif is_worthy(text):
            # Valid reply - welcome the user
            await _delete_user_rel_messages(update.effective_chat.id, user_id, context)
            sqlite_db.delete_quarantine_user(user_id=cast(int, user["_id"]))
            if update.message is not None:
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
    user = sqlite_db.find_quarantine_user(user_id)
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
        if sqlite_db.find_quarantine_user(user.id) is not None:
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

    for user in sqlite_db.find_all_quarantine_users():
        if _is_time_gone(user):
            user_id = int(user["_id"])
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await _delete_user_rel_messages(chat_id, user_id, context)
            except BadRequest as err:
                logger.error("can't ban user %s, because of: %s", user, err)
                continue

            sqlite_db.delete_quarantine_user(user_id)

            logger.info("user banned: %s", user)
