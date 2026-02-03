import logging

from telegram import Update, User
from telegram.ext import Application, ContextTypes

from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)


def add_ban(app: Application, handlers_group: int):
    logger.info("registering ban handlers")
    app.add_handler(ChatCommandHandler("ban", ban), group=handlers_group)


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
