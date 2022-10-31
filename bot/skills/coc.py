import logging

from telegram import Update
from telegram.ext import Updater, CallbackContext

from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

COC_LINK = "https://devfest.gdgvl.ru/ru/code-of-conduct/"


def add_coc(upd: Updater, handlers_group: int):
    logger.info("registering CoC handler")
    dp = upd.dispatcher
    dp.add_handler(ChatCommandHandler("coc", coc), handlers_group)


def coc(update: Update, context: CallbackContext):
    result = context.bot.send_message(
        update.effective_chat.id, f"Please behave! {COC_LINK}"
    )
    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )
