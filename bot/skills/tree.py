import logging
from datetime import datetime
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes

from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

now = datetime.now()
year = now.year
if now.month < 12:
    year -= 1

AOC_LEADERBOARD_LINK = (
    f"https://adventofcode.com/{year}/leaderboard/private/view/458538"
)


App = Application[Any, Any, Any, Any, Any, Any]


def add_tree(app: App, handlers_group: int):
    logger.info("registering tree handlers")
    app.add_handler(ChatCommandHandler("tree", tree), group=handlers_group)


async def tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"🎄🎄🎄 Присоединяйся к ежегодному решению елки! 🎄🎄🎄 \n"
        f"👉👉👉 https://adventofcode.com/ 👈👈👈 \n"
        f"😼😼😼 VLDC leaderboard: {AOC_LEADERBOARD_LINK} \n"
        f"Join Code: `458538-e2a0698b`"
    )

    if update.effective_chat is None:
        return
    await context.bot.send_message(update.effective_chat.id, text)
