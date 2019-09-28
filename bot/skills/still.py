import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, run_async, CallbackContext

logger = logging.getLogger(__name__)


def add_still(upd: Updater, handlers_group: int):
    logger.info("registering still handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("still", still), handlers_group)


@run_async
def still(update: Update, context: CallbackContext):
    text = " ".join(context.args)
    chat_id = update.effective_chat.id
    if text:
        context.bot.send_message(chat_id, f"Вот бы сейчас {text} в 2k19 лул 😹😹😹")
