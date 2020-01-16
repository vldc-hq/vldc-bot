import logging
import random

from telegram import Update
from telegram.ext import MessageHandler, Updater, CallbackContext, run_async

from filters import uwu_filter

logger = logging.getLogger(__name__)


def add_uwu(upd: Updater, handlers_group: int):
    logger.info("register uwu handlers")
    dp = upd.dispatcher
    dp.add_handler(MessageHandler(uwu_filter, uwu), handlers_group)


@run_async
def uwu(update: Update, context: CallbackContext):
    well_prepared_anti_UwU_imgs = [
        'AgADAgADiqwxG2pVAAFJ2TIJLoDENOSxBcEOAAQBAAMCAANtAAO1lQEAARYE',
        'AgADAgADiawxG2pVAAFJU823IoEQJvfOpcIPAAQBAAMCAANtAAOpKwMAARYE',
        'AgADAgADiqwxG2pVAAFJ2TIJLoDENOSxBcEOAAQBAAMCAANtAAO1lQEAARYE'
    ]
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    fairly_random_pic = random.choice(well_prepared_anti_UwU_imgs)
    context.bot.send_photo(chat_id, reply_to_message_id=message_id, photo=fairly_random_pic, caption="don't uwu! 😡")
