"""
    VLDC Nyan bot
    ~=~=~=~=~=~=~=~=~=~=~=~=~=[,,_,,]:3

    https://github.com/egregors/vldc-bot
"""
import logging

from telegram.ext import Updater
from telegram.ext.dispatcher import DEFAULT_GROUP

from config import get_config
from skills import skills

__version__ = "0.7"


def main():
    conf = get_config()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG if conf["DEBUG"] else logging.INFO)

    updater = Updater(conf["TOKEN"], use_context=True)

    for handler_group, skill in enumerate(skills, DEFAULT_GROUP + 1):
        skill["add_handlers"](updater, handler_group)

    # let's go dude
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
