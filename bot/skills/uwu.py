import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, run_async

logger = logging.getLogger(__name__)


def add_uwu(upd: Updater, handlers_group: int):
    logger.info("register uwu handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("uwu", uwu), handlers_group)


@run_async
def uwu(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_photo(chat_id, "https://i.redd.it/cqpuzj8avzh11.png", "don't uwu! 😡")
