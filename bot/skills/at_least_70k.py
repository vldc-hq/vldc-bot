import logging
import asyncio

from telegram import Update, User
from telegram.ext import Application, CallbackContext

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

MSG = (
    "Значительно больше откликов на предложение можно получить, "
    "если подробно изложить суть, приложив по возможности ссылку на описание и "
    "указав вилку :3"
)


def add_70k(application: Application, handlers_group: int):
    logger.info("registering 70k handler")
    application.add_handler(ChatCommandHandler("70k", _70k), handlers_group)


async def _70k(update: Update, context: CallbackContext):
    user: User = (
        update.message.reply_to_message.from_user
        if update.message.reply_to_message
        else None
    )
    msg = f"@{user.username} " + MSG if user else MSG
    await context.bot.send_message(update.effective_chat.id, msg)
