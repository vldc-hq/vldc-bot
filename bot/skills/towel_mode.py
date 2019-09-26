import datetime
import logging

from telegram import Update, User, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import run_async, MessageHandler, Filters, Updater, CallbackContext, CallbackQueryHandler

from config import get_config

logger = logging.getLogger(__name__)

QUARANTINE_STORE_KEY = "towel_mode__quarantine"
QUARANTINE_MIN_STORE_KEY = "towel_mode__quarantine_min"
MAGIC_NUMBER = "42"

conf = get_config()


def add_towel_mode(upd: Updater, towel_mode_handlers_group: int):
    logger.info("register towel-mode handlers")
    dp = upd.dispatcher

    # catch all new users and drop the towel
    dp.add_handler(MessageHandler(
        Filters.status_update.new_chat_members, put_new_users_in_quarantine),
        towel_mode_handlers_group
    )

    # remove messages from users from quarantine
    dp.add_handler(MessageHandler(
        Filters.group & ~Filters.status_update, check_for_reply),
        towel_mode_handlers_group
    )

    # catch "I am not a bot" button press
    dp.add_handler(CallbackQueryHandler(butt_press))

    # kick all not replied users (check every minutes)
    upd.job_queue.run_repeating(callback_minute, interval=60, first=60, context={
        "chat_name": conf["GROUP_CHAT_ID"]
    })


def get_quarantine_and_quarantine_min(context: CallbackContext):
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
    logger.info(f"put {user} in quarantine")
    quarantine, quarantine_min = get_quarantine_and_quarantine_min(context)
    minute = datetime.datetime.utcnow().minute
    quarantine[user.id] = minute
    quarantine_min[minute].append(user.id)

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Я не бот!", callback_data=MAGIC_NUMBER)]])
    context.bot.send_message(
        chat_id,
        f"{user.name} Нажми кнопку ниже, чтобы доказать, что ты не бот.\n"
        "Я буду удалять твои сообщения, пока ты не сделаешь это.\n"
        "А коли не сделаешь, через час выкину из чата.\n"
        "Ничего личного, просто боты одолели.\n",
        reply_markup=markup
    )


@run_async
def check_for_reply(update: Update, context: CallbackContext):
    quarantine, quarantine_min = get_quarantine_and_quarantine_min(context)
    minute = quarantine.get(update.effective_user.id)
    if minute is None:
        return

    logger.debug(
        f"delete msg from user: {update.effective_user} [quarantine]")
    context.bot.delete_message(
        update.effective_chat.id,
        update.effective_message.message_id, 10
    )


@run_async
def butt_press(update: Update, context: CallbackContext):
    quarantine, quarantine_min = get_quarantine_and_quarantine_min(context)
    minute = quarantine.get(update.effective_user.id)
    if minute is None:
        return
    chat_id = update.effective_chat.id
    user = update.effective_user
    query = update.callback_query
    if query.data == MAGIC_NUMBER:
        logger.info(
            f"remove user: {user.name} from quarantine")
        del (quarantine[user.id])
        quarantine_min[minute].remove(user.id)
        context.bot.send_message(
            chat_id, f"{user.name} Добро пожаловать в VLDC! 😼")


@run_async
def callback_minute(context: CallbackContext):
    chat_id = context.bot.get_chat(chat_id=context.job.context["chat_name"]).id
    logger.debug(f"get chat.id: {chat_id}")

    # sorry about that
    chat_data = context._dispatcher.chat_data.get(chat_id)  # noqa

    if chat_data is not None:
        context.chat_data = {
            QUARANTINE_STORE_KEY: chat_data[QUARANTINE_STORE_KEY],
            QUARANTINE_MIN_STORE_KEY: chat_data[QUARANTINE_MIN_STORE_KEY]
        }

        try:
            kick_users(chat_id, context)
        except Exception as e:
            logger.exception(e)
        return

    logger.debug("chat_data context is empty, skipped")


@run_async
def kick(chat_id: int, user_id: int, bot: Bot):
    logger.debug(f"kick user: {user_id}")
    if not bot.kick_chat_member(chat_id, user_id):
        logger.info(f"failed to kick user {user_id}")


@run_async
def kick_users(chat_id: int, context: CallbackContext):
    logger.debug(f"kick users context: {context.chat_data}")
    bot = context.bot
    quarantine, quarantine_min = get_quarantine_and_quarantine_min(context)
    minute = (datetime.datetime.utcnow().minute + 1) % len(quarantine_min)
    slowpokes = list([x for x in quarantine_min[minute]])
    for user_id in slowpokes:
        try:
            kick(chat_id, user_id, bot)
            logger.info(f"remove user: {user_id} from quarantine")
            quarantine_min[minute].remove(user_id)
            quarantine.pop(user_id)
        except Exception as e:
            logger.exception(e)
