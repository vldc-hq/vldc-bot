import logging

from telegram import Update, User
from telegram.ext import Updater, Dispatcher, CommandHandler, CallbackContext, run_async

logger = logging.getLogger(__name__)

MSG = f"Would you like to make PR for this?\n" \
      f"You can start by forking me at https://github.com/egregors/vldc-bot\n" \
      f"💪😎"


def add_pr(upd: Updater, handlers_group: int):
    logger.info("registering PR handler")
    dp: Dispatcher = upd.dispatcher
    dp.add_handler(CommandHandler("pr", _pr), handlers_group)


@run_async
def _pr(update: Update, context: CallbackContext):
    user: User = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    msg = f"@{user.username} " + MSG if user else MSG
    context.bot.send_message(update.effective_chat.id, msg)
