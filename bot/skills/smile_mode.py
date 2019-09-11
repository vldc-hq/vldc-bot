import logging

from telegram import Update
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, Updater, CallbackContext

from filters import admin_filter

SMILE_MODE_STORE_KEY = "is_smile_mode_on"
ON, OFF = True, False

logger = logging.getLogger(__name__)


def add_smile_mode_handlers(upd: Updater, smile_mode_handlers_group: int):
    """ Set up all handler for SmileMode """
    logger.debug("register smile-mode handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("smile_mode_on", smile_mode_on, filters=admin_filter), smile_mode_handlers_group)
    dp.add_handler(CommandHandler("smile_mode_off", smile_mode_off, filters=admin_filter), smile_mode_handlers_group)
    dp.add_handler(MessageHandler(Filters.all, smile), smile_mode_handlers_group)


def get_smile_mode(context: CallbackContext) -> bool:
    """ Get global value of SmileMode """
    return OFF \
        if SMILE_MODE_STORE_KEY not in context.chat_data \
        else context.chat_data[SMILE_MODE_STORE_KEY]


def set_smile_mode(mode: bool, context: CallbackContext):
    """ Get global value of SmileMode """
    context.chat_data[SMILE_MODE_STORE_KEY] = mode


@run_async
def smile_mode_on(update: Update, context: CallbackContext):
    """ SmileMode ON"""
    logger.debug("smile-mode switch to ON")
    is_on = get_smile_mode(context)
    if is_on is False:
        msg = context.bot.send_message(update.effective_chat.id, "SmileMode is ON 🙊")
        context.bot.pin_chat_message(
            update.effective_chat.id,
            msg.message_id,
            disable_notification=True
        )
        set_smile_mode(OFF, context)


@run_async
def smile_mode_off(update: Update, context: CallbackContext):
    """ SmileMode OFF """
    logger.debug("smile-mode switch to OFF")
    is_on = get_smile_mode(context)
    if is_on is True:
        context.bot.send_message(update.effective_chat.id, "SmileMode is OFF 🙈")
        context.bot.unpin_chat_message(update.effective_chat.id)
        set_smile_mode(ON, context)


@run_async
def smile(update: Update, context: CallbackContext):
    """ Delete all messages except stickers or GIFs """
    is_on = get_smile_mode(context)
    if is_on:
        context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id, 10
        )
