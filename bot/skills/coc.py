import logging
from datetime import datetime, timedelta
from random import randint
from threading import Lock
from typing import List, Tuple

from telegram import Update, User
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from mode import cleanup

logger = logging.getLogger(__name__)

COC_LINK = "https://devfest.gdgvl.ru/ru/code-of-conduct/"


def add_coc(upd: Updater, handlers_group: int):
    logger.info("registering CoC handler")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("coc", coc), handlers_group)


@run_async
@cleanup(seconds=600, remove_cmd=True, remove_reply=True)
def coc(update: Update, context: CallbackContext):
    context.bot.send_message(update.effective_chat.id,
                             f"Please behave! {COC_LINK}")
