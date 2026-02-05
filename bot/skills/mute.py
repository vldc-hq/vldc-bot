import logging
from datetime import datetime, timedelta
from random import choice
from typing import List

from telegram import Update, User, ChatPermissions
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from mode import cleanup_queue_update
from handlers import ChatCommandHandler
from utils.time import get_duration
from typing_utils import App, get_job_queue

logger = logging.getLogger(__name__)

MIN_MUTE_TIME = timedelta(minutes=1)
MAX_MUTE_TIME = timedelta(days=365)


def add_mute(app: App, handlers_group: int):
    logger.info("registering mute handlers")
    app.add_handler(
        ChatCommandHandler(
            "mute",
            mute,
            require_admin=True,
        ),
        group=handlers_group,
    )
    app.add_handler(ChatCommandHandler("mute", mute_self), group=handlers_group)
    app.add_handler(
        ChatCommandHandler(
            "unmute",
            unmute,
            require_admin=True,
        ),
        group=handlers_group,
    )


def _get_minutes(args: List[str]) -> timedelta:
    # cmd should be a reply for going to mute user message like "/mute 90"
    if len(args) < 1:
        raise Exception(
            "mute cmd should be a reply for going to mute user message like '/mute 90', "
            "where '90' is duration of the mute"
        )
    return get_duration(args[0])


async def mute_user_for_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user: User,
    mute_duration: timedelta,
):
    if update.message is None or update.effective_chat is None:
        return
    message = update.message
    mute_duration = max(mute_duration, MIN_MUTE_TIME)
    mute_duration = min(mute_duration, MAX_MUTE_TIME)
    try:
        until = datetime.now() + mute_duration
        logger.info(
            "user: %s[%d] will be muted for %s", user.full_name, user.id, mute_duration
        )

        await message.reply_text(f"Таймаут для {user.full_name} на {mute_duration}")
        mute_perm = ChatPermissions(
            can_add_web_page_previews=False,
            can_send_other_messages=False,
            can_send_messages=False,
            can_send_polls=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
        )
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id, mute_perm, until
        )
    except TelegramError as err:
        logger.error("can't mute user %s: %s", user, err)
        await message.reply_text(f"😿 не вышло, потому что: \n\n{err}")


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.reply_to_message is None:
        return
    user: User | None = update.message.reply_to_message.from_user
    if user is None:
        return
    args = context.args or []
    mute_minutes = _get_minutes(args)
    await mute_user_for_time(update, context, user, mute_minutes)


async def mute_self(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: User | None = update.effective_user
    if user is None:
        return
    if update.message is None:
        return
    message = update.message
    await mute_user_for_time(update, context, user, timedelta(days=1))
    self_mute_messages = [
        f"Да как эта штука работает вообще, {user.name}?",
        f"Не озоруй, {user.name}, мало ли кто увидит",
        f"Зловив {user.name} на вила!",
        f"Насилие порождает насилие, {user.name}",
        f"Опять ты, {user.name}!",
    ]
    result = await message.reply_text(choice(self_mute_messages))

    cleanup_queue_update(
        get_job_queue(context),
        message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )


async def unmute_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user: User
) -> None:
    if update.message is None or update.effective_chat is None:
        return
    message = update.message
    try:
        await message.reply_text(f"{user.full_name}, не озоруй! Мало ли кто увидит 🧐")
        unmute_perm = ChatPermissions(
            can_add_web_page_previews=True,
            can_send_other_messages=True,
            can_send_messages=True,
            can_send_polls=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
            can_invite_users=True,
        )
        await context.bot.restrict_chat_member(
            update.effective_chat.id, user.id, unmute_perm
        )
    except TelegramError as err:
        await message.reply_text(f"😿 не вышло, потому что: \n\n{err}")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.reply_to_message is None:
        return
    user: User | None = update.message.reply_to_message.from_user
    if user is None:
        return
    await unmute_user(update, context, user)
