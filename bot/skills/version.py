import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, run_async

from bot import __version__
from filters import admin_filter

logger = logging.getLogger(__name__)


def add_version_handlers(upd: Updater, version_handlers_group: int):
    logger.info("register version handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("version", version, filters=admin_filter), version_handlers_group)


@run_async
def version(update: Update, context: CallbackContext):
    """ Reply current bot version """
    logger.info(f"current ver.: {__version__}")

    chat_id = update.effective_chat.id

    context.bot.send_message(
        chat_id, f"Current version: {__version__} 😽😽")
