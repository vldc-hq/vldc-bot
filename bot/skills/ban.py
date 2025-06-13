import logging

# asyncio removed
# Union removed

from telegram import Update, User
from telegram.ext import Application, CallbackContext

from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)


def add_ban(application: Application, handlers_group: int):
    logger.info("registering ban handlers")
    application.add_handler(ChatCommandHandler("ban", ban), handlers_group)


async def ban(update: Update, context: CallbackContext):
    user: User = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    if user and chat_id:
        result = await context.bot.send_message(
            chat_id, f"Пользователь {user.name} был забанен"
        )
        cleanup_queue_update(
            context.job_queue,
            update.message,
            result,
            600,
            remove_cmd=True,
            remove_reply=False,
        )
