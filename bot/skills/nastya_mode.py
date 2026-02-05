import logging
from datetime import timedelta
from typing import Any

from telegram import Update, User
from telegram.ext import MessageHandler, ContextTypes, filters
from typing_utils import App

from mode import Mode
from skills.mute import mute_user_for_time
from utils.recognition import get_recognized_text

logger = logging.getLogger(__name__)

mode = Mode(mode_name="nastya_mode", default=True)

MAX_DURATION = 60  # seconds
VOICE_USER_MUTE_DURATION = timedelta(weeks=1)
EXCLUDING = ["@ravino_doul"]


@mode.add
def add_nastya_mode(app: App, handlers_group: int):
    logger.info("registering nastya handlers")

    app.add_handler(
        MessageHandler(
            (filters.VOICE | filters.VIDEO_NOTE) & ~filters.StatusUpdate.ALL,
            handle_nastya_mode,
            block=False,
        ),
        group=handlers_group,
    )


async def handle_nastya_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: User | None = update.effective_user
    if user is None:
        return
    if update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    message = update.message
    if message is None:
        return

    if user.name in EXCLUDING:
        return

    message_type = message.voice or message.video_note
    if message_type is None:
        return
    message_text = _compose_message_text(user, message_type)
    if message_text is None:
        return

    await context.bot.send_message(chat_id=chat_id, text=message_text)

    try:
        await mute_user_for_time(update, context, user, VOICE_USER_MUTE_DURATION)
    finally:
        await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)


def _get_duration_seconds(duration: int | float | timedelta) -> int:
    if isinstance(duration, timedelta):
        return int(duration.total_seconds())
    return int(duration)


def _compose_message_text(user: User, message_type: Any) -> str | None:
    duration_seconds = _get_duration_seconds(message_type.duration)
    if duration_seconds > MAX_DURATION:
        return f"🤫🤫🤫 @{user.username}! Слишком много наговорил..."

    file_id = message_type.file_id
    logger.info("%s sent message!", user.name)
    default_message = f"@{user.username} промямлил что-то невразумительное..."
    recognized_text = None

    try:
        recognized_text = get_recognized_text(file_id)
    except (AttributeError, ValueError, RuntimeError) as err:
        logger.exception("failed to recognize speech: %s", err)

    if recognized_text is None:
        return default_message
    return (
        f"🤫🤫🤫 Групповой чат – не место для войсов и кружочков, @{user.username}!"
        f"\n@{user.username} пытался сказать: {recognized_text}"
    )
