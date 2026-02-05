import logging

from telegram import Update
from telegram.ext import ContextTypes
from typing_utils import App, get_job_queue

from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

COC_LINK = "https://devfest.gdgvl.ru/ru/code-of-conduct/"


def add_coc(app: App, handlers_group: int):
    logger.info("registering CoC handler")
    app.add_handler(ChatCommandHandler("coc", coc), group=handlers_group)


async def coc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat is None:
        return
    result = await context.bot.send_message(
        update.effective_chat.id, f"Please behave! {COC_LINK}"
    )
    cleanup_queue_update(
        get_job_queue(context),
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )
