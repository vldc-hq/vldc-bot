import logging
from datetime import datetime, timedelta
from random import choice
from typing import List

from telegram import Update, User, ChatPermissions, TelegramError
from telegram.ext import Updater, CallbackContext

from filters import admin_filter
from mode import cleanup_queue_update
from skills import ChatCommandHandler
from utils.time import get_duration

logger = logging.getLogger(__name__)

MIN_MUTE_TIME = timedelta(minutes=1)
MAX_MUTE_TIME = timedelta(days=365)


def add_mute(upd: Updater, handlers_group: int):
    logger.info("registering mute handlers")
    dp = upd.dispatcher
    dp.add_handler(
        ChatCommandHandler(
            "mute",
            mute,
            filters=admin_filter,
        ),
        handlers_group,
    )
    dp.add_handler(ChatCommandHandler("mute", mute_self), handlers_group)
    dp.add_handler(
        ChatCommandHandler(
            "unmute",
            unmute,
            filters=admin_filter,
        ),
        handlers_group,
    )


def _get_minutes(args: List[str]) -> timedelta:
    # cmd should be a reply for going to mute user message like "/mute 90"
    if len(args) < 1:
        raise Exception(
            "mute cmd should be a reply for going to mute user message like '/mute 90', "
            "where '90' is duration of the mute"
        )
    return get_duration(args[0])


def mute_user_for_time(
    update: Update, context: CallbackContext, user: User, mute_duration: timedelta
):
    mute_duration = max(mute_duration, MIN_MUTE_TIME)
    mute_duration = min(mute_duration, MAX_MUTE_TIME)
    try:
        until = datetime.now() + mute_duration
        logger.info(
            "user: %s[%d] will be muted for %s", user.full_name, user.id, mute_duration
        )

        update.message.reply_text(f"Таймаут для {user.full_name} на {mute_duration}")
        mute_perm = ChatPermissions(
            can_add_web_page_previews=False,
            can_send_media_messages=False,
            can_send_other_messages=False,
            can_send_messages=False,
            can_send_polls=False,
        )
        context.bot.restrict_chat_member(
            update.effective_chat.id, user.id, mute_perm, until
        )
    except TelegramError as err:
        logger.error("can't mute user %s: %s", user, err)
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")


def mute(update: Update, context: CallbackContext):
    user: User = update.message.reply_to_message.from_user
    mute_minutes = _get_minutes(context.args)
    mute_user_for_time(update, context, user, mute_minutes)


def mute_self(update: Update, context: CallbackContext):
    user: User = update.effective_user
    mute_user_for_time(update, context, user, timedelta(days=1))
    self_mute_messages = [
        f"Да как эта штука работает вообще, {user.name}?",
        f"Не озоруй, {user.name}, мало ли кто увидит",
        f"Зловив {user.name} на вила!",
        f"Насилие порождает насилие, {user.name}",
        f"Опять ты, {user.name}!",
    ]
    result = update.message.reply_text(choice(self_mute_messages))

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )


def unmute_user(update: Update, context: CallbackContext, user: User) -> None:
    try:
        update.message.reply_text(f"{user.full_name}, не озоруй! Мало ли кто увидит 🧐")
        unmute_perm = ChatPermissions(
            can_add_web_page_previews=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_send_messages=True,
            can_send_polls=True,
            can_invite_users=True,
        )
        context.bot.restrict_chat_member(update.effective_chat.id, user.id, unmute_perm)
    except TelegramError as err:
        update.message.reply_text(f"😿 не вышло, потому что: \n\n{err}")


def unmute(update: Update, context: CallbackContext) -> None:
    user = update.message.reply_to_message.from_user
    unmute_user(update, context, user)
