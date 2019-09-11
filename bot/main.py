"""
    VLDC Nyan bot
    =============

    ~=[,,_,,]:3

    https://github.com/egregors/vldc-bot
"""
import logging

from telegram.ext import Updater

from config import get_config
from skills.core import add_core_handlers
from skills.smile_mode import add_smile_mode_handlers
from skills.towel_mode import add_towel_mode_handlers


def main():
    """ Start the Smile! 😊."""
    conf = get_config()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG if conf["DEBUG"] else logging.INFO)

    updater = Updater(conf["TOKEN"], use_context=True)

    add_core_handlers(updater)
    add_smile_mode_handlers(updater)
    add_towel_mode_handlers(updater)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
