import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, run_async

__version__ = "0.2"
from filters import admin_filter

logger = logging.getLogger(__name__)


def add_version(upd: Updater, version_handlers_group: int):
    logger.info("register version handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("version", version, filters=admin_filter), version_handlers_group)


@run_async
def version(update: Update, context: CallbackContext):
    """ Show current version of bot """
    logger.info(f"current ver.: {__version__}")

    chat_id = update.effective_chat.id

    context.bot.send_message(
        chat_id, f"😽 ver.: {__version__}")
