"""
    VLDC Nyan bot
    =============

    ~=[,,_,,]:3

    https://github.com/egregors/vldc-bot
"""
import logging
import os

from telegram.ext import Updater, MessageHandler, Filters

from bot.skills.core import add_core_handlers
from bot.skills.smile_mode import add_smile_mode_handlers
from bot.skills.towel_mode import add_towel_mode_handlers

DEBUG = os.getenv("DEBUG", False)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG if DEBUG else logging.INFO)


def get_chat_id() -> str:
    chat_id = os.getenv("CHAT_ID", None)
    if chat_id is None:
        raise ValueError("can't get CHAT_ID")
    return chat_id

GROUP_CHAT_ID = '@dev_smile_test' if DEBUG else get_chat_id()


def get_token() -> str:
    token = os.getenv("TOKEN", None)
    if token is None:
        raise ValueError("can't get tg token")
    return token


def main():
    """ Start the Smile! 😊."""
    TOKEN = get_token()
    updater = Updater(TOKEN, use_context=True)

    # core
    add_core_handlers(updater)

    # smile-mode
    add_smile_mode_handlers(updater)

    # towel-mode
    add_towel_mode_handlers(updater)
    # on user join start quarantine mode

    # todo: for what?
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
