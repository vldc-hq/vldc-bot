import logging

from typing import Callable

from telegram import Update, User
from telegram.error import BadRequest
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, run_async

from mode import Mode, OFF

logger = logging.getLogger(__name__)

mode = Mode(mode_name="fools_mode", default=OFF)


@mode.add
def add_fools_mode(upd: Updater, handlers_group: int):
    logger.info("registering fools handlers")
    dp = upd.dispatcher

    dp.add_handler(MessageHandler(Filters.group & ~Filters.status_update, translate_msg), handlers_group)


@run_async
def translate_msg(update: Update, context: CallbackContext):
    text = update.message['text']
    user: User = update.effective_user
    chat_id = update.effective_chat.id

    try:
        context.bot.delete_message(chat_id, update.effective_message.message_id)
    except BadRequest as err:
        logger.info(f"can't delete msg: {err}")

    try:
        context.bot.send_message(chat_id, f"{user.full_name} diris: {traduki(text)}")
    except Exception as err:
        logger.info(f"can't translate msg: {text}, because of: {err}")


def _make_traduki(f: Callable[[str], str]) -> Callable[[str], str]:
    def tr(s: str) -> str:
        if len(s) < 1:
            raise ValueError("nothing to translate")
        return f(s)

    return tr


# TODO: put your translate function here instead of lambda
#  vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
traduki = _make_traduki(lambda x: x)
