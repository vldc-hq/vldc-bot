import datetime
import logging
from typing import List, Dict

from telegram import Update, User
from telegram.ext import run_async, MessageHandler, Filters, Updater, CallbackContext

logger = logging.getLogger(__name__)

QUARANTINE_STORE_KEY = "quarantine"
QUARANTINE_MIN_STORE_KEY = "quarantine_min"


def add_towel_mode_handlers(upd: Updater, towel_mode_handlers_group: int):
    logger.debug("register towel-mode handlers")
    dp = upd.dispatcher

    # catch all new users and drop the towel
    dp.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, put_new_users_in_quarantine),
        towel_mode_handlers_group
    )

    # remove messages from users in quarantine
    dp.add_handler(MessageHandler(
        Filters.group & ~Filters.status_update, welcome),
        towel_mode_handlers_group
    )

    # upd.job_queue.run_repeating(callback_minute, interval=60, first=60, context=True)


def get_quarantine_and_quarantine_min(context: CallbackContext) -> (Dict, List):
    logger.debug("get quarantine and quarantine_min from context.chat_data")
    if QUARANTINE_STORE_KEY not in context.chat_data:
        context.chat_data[QUARANTINE_STORE_KEY] = {}

    if QUARANTINE_MIN_STORE_KEY not in context.chat_data:
        context.chat_data[QUARANTINE_MIN_STORE_KEY] = [[] for _ in range(60)]

    return context.chat_data[QUARANTINE_STORE_KEY], context.chat_data[QUARANTINE_MIN_STORE_KEY]


@run_async
def put_new_users_in_quarantine(update: Update, context: CallbackContext):
    for user in update.message.new_chat_members:
        quarantine_user(user, update.effective_chat.id, context)


@run_async
def quarantine_user(user: User, chat_id: str, context: CallbackContext) -> None:
    """ Show welcome msg and put user into quarantine """
    logger.debug(f"put {user} in quarantine")
    quarantine, quarantine_min = get_quarantine_and_quarantine_min(context)
    minute = datetime.datetime.utcnow().minute
    quarantine[user.id] = minute
    quarantine_min[minute].append(user.id)
    context.bot.send_message(
        chat_id,
        f"{user.name} Reply to me within an hour to prove you are not a bot.\n"
        "I will delete your messages in the group chat until you do this.\n"
        "If you won't answer in an hour, I'll kick you.\n"
        "Sorry for the inconvenience, we have zero tolerance for unsolicited bots.\n"
        "If you believe you were banned unfair, try to text someone from admins directly:\n"
        "@cpro29a @grawlcore @egregors\n"
    )


@run_async
def welcome(update: Update, context: CallbackContext):
    quarantine, quarantine_min = get_quarantine_and_quarantine_min(context)
    minute = quarantine.get(update.effective_user.id)
    if minute is None:
        return

    if update.effective_message.reply_to_message is not None and \
            update.effective_message.reply_to_message.from_user.id == context.bot.get_me().id:
        logger.debug(f"remove user: {update.effective_user} from quarantine")
        del (quarantine[update.effective_user.id])
        quarantine_min[minute].remove(update.effective_user.id)
        update.message.reply_text("Welcome to VLDC! 😼")
    else:
        logger.debug(f"delete msg from user: {update.effective_user} [quarantine]")
        context.bot.delete_message(
            update.effective_chat.id,
            update.effective_message.message_id, 10
        )

#
# def callback_minute(context: telegram.ext.CallbackContext):
#     logger.debug(context)
#     logger.debug(context.user_data)
#     logger.debug(context.chat_data)
#     GROUP_CHAT_ID = '@dev_smile_test'
#     try:
#         kick_users(GROUP_CHAT_ID, context)
#     except Exception as e:
#         logger.exception(e)
#
#
# def kick(chat_id, user_id, bot):
#     if not bot.kick_chat_member(chat_id, user_id):
#         logger.log(logging.INFO, "failed to kick user {}".format(user_id))
#
#
# def kick_users(chat_id, context: telegram.ext.CallbackContext):
#     bot = context.bot
#     QUARANTINE, QUARANTINE_MIN = get_quarantine_and_quarantine_min(context)
#     minute = (datetime.datetime.utcnow().minute + 1) % len(QUARANTINE_MIN)
#     slowpokes = list([x for x in QUARANTINE_MIN[minute]])
#     for user_id in slowpokes:
#         try:
#             kick(chat_id, user_id, bot)
#             del (QUARANTINE, user_id)
#             QUARANTINE_MIN[minute].remove(user_id)
#         except Exception as e:
#             logger.exception(e)
#
#
