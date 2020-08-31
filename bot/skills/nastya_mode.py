import logging
from datetime import timedelta

from telegram import Update, User
from telegram.ext import Updater, Dispatcher, MessageHandler, Filters, run_async, CallbackContext

from mode import Mode
from skills.mute import mute_user_for_time

logger = logging.getLogger(__name__)

mode = Mode(mode_name="nastya_mode", default=True)


@mode.add
def add_nastya_mode(upd: Updater, handlers_group: int):
    logger.info("registering nastya handlers")
    dp: Dispatcher = upd.dispatcher

    dp.add_handler(MessageHandler(Filters.voice & ~ Filters.status_update, handle_voice), handlers_group)


@run_async
def handle_voice(update: Update, context: CallbackContext):
    user: User = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message

    logger.info("%s sent voice message!", user.name)

    # TODO: Recognize voice message and replace original message by text

    # ban user
    context.bot.send_message(chat_id=chat_id, text=f"🤫🤫🤫 Групповой чат – не место для войсов, @{user.username}!")
    mute_user_for_time(update, context, user, timedelta(hours=2))

    # remove message
    context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
