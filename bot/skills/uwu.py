import logging, random

from telegram import Update
from telegram.ext import CommandHandler, Updater, CallbackContext, run_async

logger = logging.getLogger(__name__)


def add_uwu(upd: Updater, handlers_group: int):
    logger.info("register uwu handlers")
    dp = upd.dispatcher
    dp.add_handler(CommandHandler("uwu", uwu), handlers_group)


@run_async
def uwu(update: Update, context: CallbackContext):

    well_prepared_anti_UwU_imgs = [
        'AgADAgADG6wxG4hCMEtTOdyVipxZzgJ-XA8ABAEAAwIAA3gAA0xGAgABFgQ',
        'AgADAgADbawxG29dMUuBUJdCgzngPjbQug8ABAEAAwIAA3gAA5sxBgABFgQ',
        'AgADAgADHawxG4hCMEv7_rCj61FgpRWqwg8ABAEAAwIAA3gAA8czAQABFgQ',
        'AgADAgADHqwxG4hCMEsTAlVxUnCKEH2Xwg8ABAEAAwIAA3gAAyg0AQABFgQ',
        'AgADAgADH6wxG4hCMEszk4hv-RkUlkVuXA8ABAEAAwIAA3gAAzpDAgABFgQ'
    ] 

    chat_id = update.effective_chat.id
    fairly_random_pic = random.choice(well_prepared_anti_UwU_imgs)
    context.bot.send_photo(chat_id, photo=fairly_random_pic, "don't uwu! 😡")
