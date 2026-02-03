import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

from mode import Mode

logger = logging.getLogger(__name__)

mode = Mode(mode_name="smile_mode", default=False, pin_info_msg=True)


@mode.add
def add_smile_mode(app: Application, handlers_group: int):
    """Set up all handler for SmileMode"""
    logger.info("registering smile-mode handlers")
    app.add_handler(
        MessageHandler(~filters.Sticker.ALL & ~filters.ANIMATION, smile, block=False),
        group=handlers_group,
    )


async def smile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete all messages except stickers or GIFs"""
    logger.debug("remove msg: %s", update.effective_message)
    await context.bot.delete_message(
        update.effective_chat.id, update.effective_message.message_id
    )
