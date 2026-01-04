"""
VLDC Nyan bot
~=~=~=~=~=~=~=~=~=~=~=~=~=[,,_,,]:3

https://github.com/vldc-hq/vldc-bot
"""

import logging

import sentry_sdk
from telegram.ext import Updater
from telegram.ext.dispatcher import DEFAULT_GROUP

from config import get_config
from skills import skills, commands_list

logger = logging.getLogger(__name__)


def main():
    """🐈🐈🐈"""
    conf = get_config()

    # pylint: disable=abstract-class-instantiated
    sentry_sdk.init(conf["SENTRY_DSN"], traces_sample_rate=1.0)

    if conf["DEBUGGER"]:
        # pylint: disable=import-outside-toplevel
        import ptvsd

        ptvsd.enable_attach(address=("0.0.0.0", 5678))
        ptvsd.wait_for_attach()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if conf["DEBUG"] else logging.INFO,
    )

    updater = Updater(conf["TOKEN"], use_context=True)

    for handler_group, skill in enumerate(skills, DEFAULT_GROUP + 1):
        skill["add_handlers"](updater, handler_group)

    # update commands list
    updater.bot.set_my_commands(commands=commands_list)

    # let's go dude
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
