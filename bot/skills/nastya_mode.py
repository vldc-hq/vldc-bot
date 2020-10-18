import logging
from datetime import timedelta
from logging import log

from telegram import Update, User
from telegram.ext import Updater, Dispatcher, MessageHandler, Filters, run_async, CallbackContext

from mode import Mode
from skills.mute import mute_user_for_time
from utils.audio_recognition import get_text_from_speech

logger = logging.getLogger(__name__)

mode = Mode(mode_name="nastya_mode", default=True)


@mode.add
def add_nastya_mode(upd: Updater, handlers_group: int):
    logger.info("registering nastya handlers")
    dp: Dispatcher = upd.dispatcher

    dp.add_handler(MessageHandler(Filters.voice & ~ Filters.status_update, handle_voice), handlers_group)
    dp.add_handler(MessageHandler(Filters.audio & ~ Filters.status_update, handle_voice), handlers_group)


@run_async
def handle_voice(update: Update, context: CallbackContext):
    user: User = update.effective_user
    chat_id = update.effective_chat.id
    message = update.message


    # remove message
    # context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)

    # TODO: Recognize voice message and replace original message by text
    voice = message.voice or message.audio
    duration = voice.duration

    message_text = ""

    if duration > 30:
        message_text = f"🤫🤫🤫 @{user.username}! Слишком много наговорил..."
    else:
        file_id = voice.file_id
        file_type = voice.mime_type

        logger.info("%s sent voice message!", user.name)
        
        logger.info("------------------------------------------------------------------------------------")
        logger.info(f"id: {file_id}, type: {file_type}")
        text = get_text_from_speech(file_id)
        logger.info("------------------------------------------------------------------------------------")

        message_text = f"🤫🤫🤫 Групповой чат – не место для войсов, @{user.username}!\n{text}"

    context.bot.send_message(chat_id=chat_id, text=message_text)
