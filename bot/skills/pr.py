import logging

from telegram import Update, User
from telegram.ext import Application, ContextTypes

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

MSG = (
    "Would you like to make PR for this?\n"
    "You can start by forking me at https://github.com/vldc-hq/vldc-bot\n"
    "💪😎"
)


def add_pr(app: Application, handlers_group: int):
    logger.info("registering PR handler")
    app.add_handler(ChatCommandHandler("pr", _pr), group=handlers_group)


async def _pr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    user: User | None = (
        update.message.reply_to_message.from_user
        if update.message.reply_to_message
        else None
    )
    msg = f"@{user.username} " + MSG if user else MSG
    await context.bot.send_message(update.effective_chat.id, msg)
