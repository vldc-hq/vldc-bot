import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, ContextTypes
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)


def add_nya(app: Application, handlers_group: int):
    logger.info("registering nya handlers")
    app.add_handler(
        ChatCommandHandler(
            "nya",
            nya,
            require_admin=True,
        ),
        group=handlers_group,
    )


async def nya(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    chat_id = update.effective_chat.id

    try:
        await context.bot.delete_message(chat_id, update.effective_message.message_id)
    except BadRequest as err:
        logger.info("can't delete msg: %s", err)

    if text:
        await context.bot.send_message(chat_id, text)
