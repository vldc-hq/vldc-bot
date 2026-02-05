import logging
import random
from typing import Any

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes

from filters import uwu_filter

logger = logging.getLogger(__name__)


# FIXME: uwu is broken: telegram.error.BadRequest: Wrong file identifier/http url specified
App = Application[Any, Any, Any, Any, Any, Any]


def add_uwu(app: App, handlers_group: int):
    logger.info("register uwu handlers")
    app.add_handler(MessageHandler(uwu_filter, uwu, block=False), group=handlers_group)


async def uwu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    well_prepared_anti_UwU_imgs = [
        "AgADAgADKqwxG9gDCEk48KXBcoIEgkpOyw4ABAEAAwIAA20AA6DsAAIWBA",
        "AgADAgADQKwxG2TDCElWC03ITmP10r5fyw4ABAEAAwIAA20AA73rAAIWBA",
        "AgADAgADQawxG2TDCEm-OKVgXYSOoxUawQ4ABAEAAwIAA20AA-aVAQABFgQ",
    ]
    if update.effective_chat is None or update.message is None:
        return
    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    fairly_random_pic = random.choice(well_prepared_anti_UwU_imgs)
    await context.bot.send_photo(
        chat_id,
        reply_to_message_id=message_id,
        photo=fairly_random_pic,
        caption="don't uwu! 😡",
    )
