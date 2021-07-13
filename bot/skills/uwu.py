import logging
import random

from telegram import Update
from telegram.ext import MessageHandler, Updater, CallbackContext

from filters import uwu_filter

logger = logging.getLogger(__name__)


# FIXME: uwu is broken: telegram.error.BadRequest: Wrong file identifier/http url specified
def add_uwu(upd: Updater, handlers_group: int):
    logger.info("register uwu handlers")
    dp = upd.dispatcher
    dp.add_handler(MessageHandler(uwu_filter, uwu, run_async=True), handlers_group)


def uwu(update: Update, context: CallbackContext):
    well_prepared_anti_UwU_imgs = [
        "AgADAgADKqwxG9gDCEk48KXBcoIEgkpOyw4ABAEAAwIAA20AA6DsAAIWBA",
        "AgADAgADQKwxG2TDCElWC03ITmP10r5fyw4ABAEAAwIAA20AA73rAAIWBA",
        "AgADAgADQawxG2TDCEm-OKVgXYSOoxUawQ4ABAEAAwIAA20AA-aVAQABFgQ",
    ]
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    fairly_random_pic = random.choice(well_prepared_anti_UwU_imgs)
    context.bot.send_photo(
        chat_id,
        reply_to_message_id=message_id,
        photo=fairly_random_pic,
        caption="don't uwu! 😡",
    )
