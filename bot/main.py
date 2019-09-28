"""
    VLDC Nyan bot
    ~=~=~=~=~=~=~=~=~=~=~=~=~=[,,_,,]:3

    https://github.com/egregors/vldc-bot
"""
import logging

from telegram.ext import Updater

from config import get_config
from skills.core import add_core
from skills.since_mode import add_since_mode
from skills.smile_mode import add_smile_mode
from skills.still import add_still
from skills.towel_mode import add_towel_mode
from skills.version import add_version


def main():
    """ Start the Smile! 😊."""
    conf = get_config()
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG if conf["DEBUG"] else logging.INFO)

    updater = Updater(conf["TOKEN"], use_context=True)

    # put each skill in the different group
    class HandlersGroups:
        core = 0
        version = 1
        still = 3

        smile_mode = 4
        tower_mode = 5
        since_mode = 6

    # init all skills
    add_core(updater, HandlersGroups.core)
    add_version(updater, HandlersGroups.version)
    add_still(updater, HandlersGroups.still)

    # modes
    add_smile_mode(updater, HandlersGroups.smile_mode)
    add_since_mode(updater, HandlersGroups.since_mode)
    add_towel_mode(updater, HandlersGroups.tower_mode)

    # let's go dude
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
