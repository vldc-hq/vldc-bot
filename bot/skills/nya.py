import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Updater, CommandHandler, CallbackContext

from filters import admin_filter, group_filter

logger = logging.getLogger(__name__)


def add_nya(upd: Updater, handlers_group: int):
    logger.info("registering nya handlers")
    dp = upd.dispatcher
    dp.add_handler(
        CommandHandler("nya", nya, filters=group_filter & admin_filter, run_async=True), handlers_group
    )


def nya(update: Update, context: CallbackContext):
    text = " ".join(context.args)
    chat_id = update.effective_chat.id

    try:
        context.bot.delete_message(chat_id, update.effective_message.message_id)
    except BadRequest as err:
        logger.info("can't delete msg: %s", err)

    if text:
        context.bot.send_message(chat_id, text)
