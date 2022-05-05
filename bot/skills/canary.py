import logging

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

logger = logging.getLogger(__name__)


def add_canary(upd: Updater, handlers_group: int):
    logger.info("registering canary handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("chirp", meow, run_async=True), handlers_group)


def meow(update: Update, context: CallbackContext):
    # TODO: https://github.com/vldc-hq/vldc-bot/issues/247
    #   I believe we could add some extra security here, like PGP sign for answer
    update.effective_chat.bot.send_message(
        chat_id=update.effective_chat.id, text="meow"
    )
