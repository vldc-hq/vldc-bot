import logging

from telegram import Update
from telegram.ext import Updater, CallbackContext

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

AOC_LEADERBOARD_LINK = "https://adventofcode.com/2022/leaderboard/private/view/458538"


def add_tree(upd: Updater, handlers_group: int):
    logger.info("registering tree handlers")
    dp = upd.dispatcher
    dp.add_handler(ChatCommandHandler("tree", tree), handlers_group)


def tree(update: Update, context: CallbackContext):
    text = (
        f"🎄🎄🎄 Присоединяйся к ежегодному решению елки! 🎄🎄🎄 \n"
        f"👉👉👉 https://adventofcode.com/ 👈👈👈 \n"
        f"😼😼😼 VLDC leaderboard: {AOC_LEADERBOARD_LINK} \n"
        f"Join Code: `458538-e2a0698b`"
    )

    context.bot.send_message(update.effective_chat.id, text)
