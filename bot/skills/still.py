import logging
from datetime import datetime

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes
from typing_utils import App

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)


def add_still(app: App, handlers_group: int):
    logger.info("registering still handlers")
    app.add_handler(ChatCommandHandler("still", still), group=handlers_group)


def to_2k_year(year: int):
    year_2k = str(year)
    if (year // 100) % 10 == 0:
        y = list(str(year))
        y[-3] = "k"
        year_2k = "".join(y)
    return year_2k


async def still(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    text = " ".join(args)
    if update.effective_chat is None or update.effective_message is None:
        return
    chat_id = update.effective_chat.id
    try:
        await context.bot.delete_message(chat_id, update.effective_message.message_id)
    except BadRequest as err:
        logger.info("can't delete msg: %s", err)

    if text:
        await context.bot.send_message(
            chat_id,
            f"Вот бы сейчас {text} в {to_2k_year(datetime.now().year)} лул 😹😹😹",
        )
