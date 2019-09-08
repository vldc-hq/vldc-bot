"""
    SmileBot

    @egregors, @cpro29a 2019
    https://github.com/egregors/smile-bot
"""
import logging
import os
import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, BaseFilter
from telegram.ext.dispatcher import run_async

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# OFF by default
SMILE_MODE = False

# map of users in quarantine
QUARANTINE = {}
# list of users in quarantine joined in a particular minute
QUARANTINE_MIN = [[] for x in range(60)]

GROUP_CHAT_ID = '@vldchat'


class _Admin(BaseFilter):
    """ Filter for messages only from admins """
    name = 'Filters.admin'

    def filter(self, message) -> bool:
        return message.from_user.id in set([a.user.id for a in message.chat.get_administrators()])


@run_async
def quarantine_user(user, chat_id, context):
    minute = datetime.datetime.utcnow().minute
    QUARANTINE[user.id] = minute
    QUARANTINE_MIN[minute].append(user.id)
    context.bot.send_message(chat_id, """{} Reply to me within an hour to prove you are not a bot.
I will delete your messages in the group chat until you do this.
If you wan't answer in ann hour, I'll kick you.
Sorry for the inconvenience, we have zero tolerance for unsolicited bots.""".format(
        user.name
    ))


@run_async
def start(update, context):
    update.message.reply_text("I'm a Smile Bot.\n\nInspired by Twitch 'SmileMode'\n"
                              "I may bring you a remarkable new way to conversation 😉\n\n"
                              "If you an admin of this Group just send '/on' to set SmileMode ON,\n"
                              "and '/off' to turn it off.\n\n"
                              "Keep it in mind, you should make me an admin and allow delete and pin messages\n"
                              "On SmileMode all messages exclude stickers of GIFs will be deleted.\n\n"
                              "Bot source: https://github.com/egregors/smile-bot")


@run_async
def help_(update, context):
    update.message.reply_text("The bot should be an admin with delete messages and pin messages permissions\n\n"
                              "'/on' – smile mode ON\n"
                              "'/off' – smile mode OFF\n")


def kick(chat_id, user_id, bot):
    if not bot.kick_chat_member(chat_id, user_id):
        logger.log(logging.INFO, "failed to kick user {}".format(user_id))


def kick_users(chat_id, bot):
    minute = (datetime.datetime.utcnow().minute + 1) % len(QUARANTINE_MIN)
    slowpokes = list([x for x in QUARANTINE_MIN[minute]])
    for user_id in slowpokes:
        kick(chat_id, user_id, bot)
        del(QUARANTINE, user_id)
        QUARANTINE_MIN[minute].remove(user_id)


def callback_minute(context: telegram.ext.CallbackContext):
    try:
        kick_users(GROUP_CHAT_ID, context.bot)
    except Exception as e:
        logger.exception(e)


def welcome(update, context):
    minute = QUARANTINE.get(update.effective_user.id)
    if minute == None:
        return
    del(QUARANTINE, update.effective_user.id)
    QUARANTINE_MIN[minute].remove(update.effective_user.id)
    update.message.reply_text("Welcome to VLDC!")


@run_async
def sml_mode_on(update, context):
    """ SmileMode ON"""
    global SMILE_MODE
    if not SMILE_MODE:
        SMILE_MODE = True
        msg = context.bot.send_message(
            update.effective_chat.id, "SmileMode is ON 🙊")
        context.bot.pin_chat_message(
            update.effective_chat.id,
            msg.message_id,
            disable_notification=True)


@run_async
def sml_mode_off(update, context):
    """ SmileMode OFF"""
    global SMILE_MODE
    if SMILE_MODE:
        SMILE_MODE = False
        context.bot.send_message(
            update.effective_chat.id, "SmileMode is OFF 🙈")
        context.bot.unpin_chat_message(update.effective_chat.id)


@run_async
def smile(update, context):
    """ Delete all messages except stickers or GIFs """
    if SMILE_MODE:
        context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id, 10)


def error(update, context):
    """ Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


@run_async
def handle_new_chat_members(update, context):
    msg = update.message
    for user in msg.new_chat_members:
        quarantine_user(user, update.effective_chat.id, context)


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

    # remove messages from users in quarantine
    dp.add_handler(MessageHandler(
        Filters.group,
        welcome))

    # on non sticker or gif message - delete the message
    dp.add_handler(MessageHandler(
        ~Filters.sticker & ~Filters.animation,
        smile))

    # on user join start quarantine mode
    dp.add_handler(MessageHandler(
        Filters.status_update.new_chat_members,
        handle_new_chat_members))

    dp.add_error_handler(error)
    j = updater.job_queue
    job_minute = j.run_repeating(callback_minute, interval=60, first=60)

    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
