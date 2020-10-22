import logging
from datetime import timedelta

from telegram import Update, User
from telegram.ext import Updater, Dispatcher, MessageHandler, Filters, run_async, CallbackContext

from mode import Mode
from skills.mute import mute_user_for_time
from utils.voice_recognition import get_text_from_speech

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

    voice = message.voice or message.audio
    duration = voice.duration

    message_text = ""

    if duration > 20:
        message_text = f"🤫🤫🤫 @{user.username}! Слишком много наговорил..."
    else:
        file_id = voice.file_id
        logger.info("%s sent voice message!", user.name)
        default_message = f"@{user.username} промямлил что-то невразумительное..."
        recognized_text = get_text_from_speech(file_id)
        if recognized_text is None:
            message_text = default_message
        else:
            message_text = f"🤫🤫🤫 Групповой чат – не место для войсов, @{user.username}!"\
                            f"\nВот такой текст был распознан: {recognized_text}"

    context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    context.bot.send_message(chat_id=chat_id, text=message_text)
