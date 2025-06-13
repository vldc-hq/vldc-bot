import logging

from datetime import datetime  # asyncio removed

from telegram import Update
from telegram.ext import Application, CallbackContext

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

now = datetime.now()
year = now.year
if now.month < 12:
    year -= 1

AOC_LEADERBOARD_LINK = (
    f"https://adventofcode.com/{year}/leaderboard/private/view/458538"
)


def add_tree(application: Application, handlers_group: int):
    logger.info("registering tree handlers")
    application.add_handler(ChatCommandHandler("tree", tree), handlers_group)


async def tree(update: Update, context: CallbackContext):
    text = (
        f"🎄🎄🎄 Присоединяйся к ежегодному решению елки! 🎄🎄🎄 \n"
        f"👉👉👉 https://adventofcode.com/ 👈👈👈 \n"
        f"😼😼😼 VLDC leaderboard: {AOC_LEADERBOARD_LINK} \n"
        f"Join Code: `458538-e2a0698b`"
    )

    await context.bot.send_message(update.effective_chat.id, text)
