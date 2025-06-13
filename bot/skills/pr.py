import logging
import asyncio

from telegram import Update, User
from telegram.ext import Application, CallbackContext

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

MSG = (
    "Would you like to make PR for this?\n"
    "You can start by forking me at https://github.com/vldc-hq/vldc-bot\n"
    "💪😎"
)


def add_pr(application: Application, handlers_group: int):
    logger.info("registering PR handler")
    application.add_handler(ChatCommandHandler("pr", _pr), handlers_group)


async def _pr(update: Update, context: CallbackContext):
    user: User = (
        update.message.reply_to_message.from_user
        if update.message.reply_to_message
        else None
    )
    msg = f"@{user.username} " + MSG if user else MSG
    await context.bot.send_message(update.effective_chat.id, msg)
