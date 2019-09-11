from telegram import Update
from telegram.ext import run_async, CommandHandler, MessageHandler, Filters, Updater, CallbackContext

from filters import admin_filter

SMILE_MODE_STORE_KEY = "is_smile_mode_on"
ON, OFF = True, False


def add_smile_mode_handlers(upd: Updater):
    """ Set up all handler for SmileMode """
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("smile_mode_on", smile_mode_on, filters=admin_filter))
    dp.add_handler(CommandHandler("smile_mode_off", smile_mode_off, filters=admin_filter))
    dp.add_handler(MessageHandler(~Filters.sticker & ~Filters.animation, smile))


def get_smile_mode(context: CallbackContext) -> bool:
    """ Get global value of SmileMode """
    return OFF \
        if SMILE_MODE_STORE_KEY not in context.chat_data \
        else context.chat_data[SMILE_MODE_STORE_KEY]


def set_smile_mode(mode: bool, context: CallbackContext):
    """ Get global value of SmileMode """
    context.chat_data[SMILE_MODE_STORE_KEY] = mode


# command handlers
@run_async
def smile_mode_on(update: Update, context: CallbackContext):
    """ SmileMode ON"""
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
