"""
    VLDC Nyan bot
    =============

    ~=[,,_,,]:3

    https://github.com/egregors/vldc-bot
"""
import datetime
import functools
import logging
import os

from telegram.ext import Updater, MessageHandler, Filters
from telegram.ext.dispatcher import run_async

from bot.skills.core import add_core_handlers
from bot.skills.smile_mode import add_smile_mode_handlers

DEBUG = os.getenv("DEBUG", False)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

# map of users in quarantine
QUARANTINE = {}
# list of users in quarantine joined in a particular minute
QUARANTINE_MIN = [[] for x in range(60)]


def get_chat_id() -> str:
    chat_id = os.getenv("CHAT_ID", None)
    if chat_id is None:
        raise ValueError("can't get CHAT_ID")
    return chat_id


GROUP_CHAT_ID = '@dev_smile_test' if DEBUG else get_chat_id()
LOG_ALL_CALLS = True if DEBUG else False


def log_call(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        global LOG_ALL_CALLS
        if LOG_ALL_CALLS:
            logging.debug("calling {}".format(f.__name__))
        return f(*args, **kwargs)

    return inner


@run_async
@log_call
def quarantine_user(user, chat_id, context) -> None:
    global QUARANTINE, QUARANTINE_MIN
    minute = datetime.datetime.utcnow().minute
    QUARANTINE[user.id] = minute
    QUARANTINE_MIN[minute].append(user.id)
    context.bot.send_message(chat_id, """{} Reply to me within an hour to prove you are not a bot.
I will delete your messages in the group chat until you do this.
If you wan't answer in ann hour, I'll kick you.
Sorry for the inconvenience, we have zero tolerance for unsolicited bots.""".format(
        user.name
    ))


@log_call
def kick(chat_id, user_id, bot):
    if not bot.kick_chat_member(chat_id, user_id):
        logger.log(logging.INFO, "failed to kick user {}".format(user_id))


@log_call
def kick_users(chat_id, bot):
    global QUARANTINE, QUARANTINE_MIN
    minute = (datetime.datetime.utcnow().minute + 1) % len(QUARANTINE_MIN)
    slowpokes = list([x for x in QUARANTINE_MIN[minute]])
    for user_id in slowpokes:
        try:
            kick(chat_id, user_id, bot)
            del (QUARANTINE, user_id)
            QUARANTINE_MIN[minute].remove(user_id)
        except Exception as e:
            logger.exception(e)


@log_call
def callback_minute(context):
    global GROUP_CHAT_ID
    try:
        kick_users(GROUP_CHAT_ID, context.bot)
    except Exception as e:
        logger.exception(e)


@run_async
@log_call
def welcome(update, context):
    global QUARANTINE, QUARANTINE_MIN
    minute = QUARANTINE.get(update.effective_user.id)
    if minute is None:
        return
    if update.effective_message.reply_to_message is not None and \
            update.effective_message.reply_to_message.from_user.id == context.bot.get_me().id:
        del (QUARANTINE[update.effective_user.id])
        QUARANTINE_MIN[minute].remove(update.effective_user.id)
        update.message.reply_text("Welcome to VLDC!")
    else:
        context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id, 10
        )


def error(update, context):
    """ Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


@run_async
@log_call
def handle_new_chat_members(update, context):
    msg = update.message
    for user in msg.new_chat_members:
        quarantine_user(user, update.effective_chat.id, context)


def get_token() -> str:
    token = os.getenv("TOKEN", None)
    if token is None:
        raise ValueError("can't get tg token")
    return token


@log_call
def main():
    """ Start the Smile! 😊."""
    TOKEN = get_token()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # core
    add_core_handlers(dp)

    # smile-mode
    add_smile_mode_handlers(dp)
    # dp.add_handler(CommandHandler("on", sml_mode_on, filters=admin_filter))

    # towel-mode
    # on user join start quarantine mode
    dp.add_handler(MessageHandler(
        Filters.status_update.new_chat_members,
        handle_new_chat_members))

    # remove messages from users in quarantine
    dp.add_handler(MessageHandler(
        Filters.group & ~Filters.status_update,
        welcome))

    dp.add_error_handler(error)
    updater.job_queue.run_repeating(callback_minute, interval=60, first=60)

    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
