import logging

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, run_async

logger = logging.getLogger(__name__)


def add_askci(upd: Updater, handlers_group: int):
    logger.info("register askci handler")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("ci", askci), handlers_group)


@run_async
def askci(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_photo(chat_id, "http://risovach.ru/upload/2011/10/comics_1318948335_orig_Bud-muzhikom-bleat.jpg", "@cpro29a, как там ci? ;)")
