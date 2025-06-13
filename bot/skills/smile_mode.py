import logging

# asyncio removed
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CallbackContext,
)  # filters re-added

# Sticker, Animation class imports removed

from mode import Mode

logger = logging.getLogger(__name__)

mode = Mode(mode_name="smile_mode", default=False, pin_info_msg=True)


@mode.add
def add_smile_mode(application: Application, handlers_group: int):
    """Set up all handler for SmileMode"""
    logger.info("registering smile-mode handlers")
    application.add_handler(
        MessageHandler(
            ~filters.STICKER & ~filters.ANIMATION, smile  # pylint: disable=no-member
        ),
        handlers_group,
    )


async def smile(update: Update, context: CallbackContext):
    """Delete all messages except stickers or GIFs"""
    logger.debug("remove msg: %s", update.effective_message)
    await context.bot.delete_message(
        update.effective_chat.id, update.effective_message.message_id, 10
    )
