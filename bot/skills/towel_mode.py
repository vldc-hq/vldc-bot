import datetime
import logging

from telegram.ext import run_async, Dispatcher, MessageHandler, Filters, Updater

logger = logging.getLogger(__name__)


def add_towel_mode_handlers(upd: Updater):
    dp = upd.dispatcher

    dp.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, handle_new_chat_members)
    )

    # remove messages from users in quarantine
    dp.add_handler(MessageHandler(
        Filters.group & ~Filters.status_update, welcome)
    )

    upd.job_queue.run_repeating(callback_minute, interval=60, first=60)


# map of users in quarantine
QUARANTINE = {}
# list of users in quarantine joined in a particular minute
QUARANTINE_MIN = [[] for x in range(60)]


@run_async
def handle_new_chat_members(update, context):
    msg = update.message
    for user in msg.new_chat_members:
        quarantine_user(user, update.effective_chat.id, context)


@run_async
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


def callback_minute(context):
    GROUP_CHAT_ID
    try:
        kick_users(GROUP_CHAT_ID, context.bot)
    except Exception as e:
        logger.exception(e)


def kick(chat_id, user_id, bot):
    if not bot.kick_chat_member(chat_id, user_id):
        logger.log(logging.INFO, "failed to kick user {}".format(user_id))


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


@run_async
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
