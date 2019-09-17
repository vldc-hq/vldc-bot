import logging

from telegram.ext import Updater, CommandHandler

logger = logging.getLogger(__name__)


def add_since_mode_handlers(upd: Updater, since_mode_handlers_group: int):
    logger.info("register since-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("since", since_callback), since_mode_handlers_group)


def since_callback(update, context):
    topic = " ".join(context.args)
    update.message.reply_text(f"This is are _ days since «{topic}» discussion")
