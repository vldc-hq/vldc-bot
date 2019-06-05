"""
    SmileBot

    @egregors 2019
    https://github.com/egregors/smile-bot
"""
import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, BaseFilter

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# OFF by default
SMILE_MODE = False


class _Admin(BaseFilter):
    """ Filter for messages only from admins """
    name = 'Filters.admin'

    def filter(self, message) -> bool:
        return message.from_user.id in [a.user.id for a in message.chat.get_administrators()]


def start(update, context):
    update.message.reply_text("I'm a Smile Bot.\n\nInspired by Twitch 'SmileMode'\n"
                              "I may bring you a remarkable new way to conversation 😉\n\n"
                              "If you an admin of this Group just send '/on' to set SmileMode ON,\n"
                              "and '/off' to turn it off.\n\n"
                              "Keep it in mind, you should make me an admin and allow delete and pin messages\n"
                              "On SmileMode all messages exclude stickers of GIFs will be deleted.\n\n"
                              "Bot source: https://github.com/egregors/smile-bot")


def help_(update, context):
    update.message.reply_text("The bot should be an admin with delete messages and pin messages permissions\n\n"
                              "'/on' – smile mode ON\n"
                              "'/off' – smile mode OFF\n")


def sml_mode_on(update, context):
    """ SmileMode ON"""
    global SMILE_MODE
    if not SMILE_MODE:
        SMILE_MODE = True
        msg = context.bot.send_message(update.effective_chat.id, "SmileMode is ON 🙊")
        context.bot.pin_chat_message(update.effective_chat.id, msg.message_id, disable_notification=True)


def sml_mode_off(update, context):
    """ SmileMode OFF"""
    global SMILE_MODE
    if SMILE_MODE:
        SMILE_MODE = False
        context.bot.send_message(update.effective_chat.id, "SmileMode is OFF 🙈")
        context.bot.unpin_chat_message(update.effective_chat.id)


def smile(update, context):
    """ Delete all messages except stickers or GIFs """
    if SMILE_MODE:
        context.bot.delete_message(update.effective_chat.id, update.effective_message.message_id, 10)


def error(update, context):
    """ Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """ Start the Smile! 😊."""
    TOKEN = os.getenv("TOKEN", None)
    if TOKEN is None:
        logger.error(msg="bad tg token")
        exit(1)

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    admin = _Admin()

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_))
    dp.add_handler(CommandHandler("on", sml_mode_on, filters=admin))
    dp.add_handler(CommandHandler("off", sml_mode_off, filters=admin))

    # on non sticker or gif message - delete the message
    dp.add_handler(MessageHandler(~Filters.sticker & ~Filters.animation, smile))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
