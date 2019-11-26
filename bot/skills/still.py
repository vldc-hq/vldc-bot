import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Updater, CommandHandler, run_async, CallbackContext

logger = logging.getLogger(__name__)


def add_still(upd: Updater, handlers_group: int):
    logger.info("registering still handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("still", still), handlers_group)


def to_2k_year(year: int):
    year_2k = str(year)
    if (year // 100) % 10 == 0:
        y = list(str(year))
        y[-3] = 'k'
        year_2k = ''.join(y)
    return year_2k


@run_async
def still(update: Update, context: CallbackContext):
    text = " ".join(context.args)
    chat_id = update.effective_chat.id
    if text:
        context.bot.send_message(chat_id, f"Вот бы сейчас {text} в {to_2k_year(datetime.now().year)} лул 😹😹😹")
