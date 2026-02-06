import logging

from telegram import Update, User
from telegram.ext import ContextTypes
from typing_utils import App

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

MSG = (
    "Значительно больше откликов на предложение можно получить, "
    "если подробно изложить суть, приложив по возможности ссылку на описание и "
    "указав вилку :3"
)


def add_70k(app: App, handlers_group: int):
    logger.info("registering 70k handler")
    app.add_handler(ChatCommandHandler("70k", _70k), group=handlers_group)


async def _70k(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    if update.effective_chat is None:
        return
    user: User | None = (
        update.message.reply_to_message.from_user
        if update.message.reply_to_message
        else None
    )
    msg = f"@{user.username} " + MSG if user else MSG
    await context.bot.send_message(update.effective_chat.id, msg)
