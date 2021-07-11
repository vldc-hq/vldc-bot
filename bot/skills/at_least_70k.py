import logging

from telegram import Update, User
from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackContext

logger = logging.getLogger(__name__)

MSG = "Значительно больше откликов на предложение можно получить, " \
      "если подробно изложить суть, приложив по возможности ссылку на описание и " \
      "указав вилку :3"


def add_70k(upd: Updater, handlers_group: int):
    logger.info("registering 70k handler")
    dp: Dispatcher = upd.dispatcher
    dp.add_handler(CommandHandler("70k", _70k, run_async=True), handlers_group)


def _70k(update: Update, context: CallbackContext):
    user: User = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    msg = f"@{user.username} " + MSG if user else MSG
    context.bot.send_message(update.effective_chat.id, msg)
