"""
VLDC Nyan bot
~=~=~=~=~=~=~=~=~=~=~=~=~=[,,_,,]:3

https://github.com/vldc-hq/vldc-bot
"""

# pylint: disable=wrong-import-position

import os
import logging

# Work around protobuf C-extension incompatibility with Python 3.14
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import sentry_sdk  # noqa: E402
from telegram.ext import ApplicationBuilder  # noqa: E402
from telegram.request import HTTPXRequest  # noqa: E402

from config import get_config  # noqa: E402
from skills import skills, commands_list  # noqa: E402

DEFAULT_GROUP = 0

logger = logging.getLogger(__name__)


async def _post_init(application):
    await application.bot.set_my_commands(commands=commands_list)
    try:
        bot_user = await application.bot.get_me()
        application.bot_data["bot_user_id"] = bot_user.id
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("failed to fetch bot user info: %s", exc)


def main():
    """🐈🐈🐈"""
    conf = get_config()

    # pylint: disable=abstract-class-instantiated
    sentry_sdk.init(conf["SENTRY_DSN"], traces_sample_rate=1.0)

    if conf["DEBUGGER"]:
        # pylint: disable=import-outside-toplevel
        import debugpy

        debugpy.listen(("0.0.0.0", 5678))
        debugpy.wait_for_client()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if conf["DEBUG"] else logging.INFO,
    )

    request = HTTPXRequest(
        connect_timeout=10,
        read_timeout=30,
        write_timeout=30,
        pool_timeout=5,
    )
    application = (
        ApplicationBuilder()
        .token(conf["TOKEN"])
        .post_init(_post_init)
        .request(request)
        .build()
    )

    for handler_group, skill in enumerate(skills, DEFAULT_GROUP + 1):
        skill["add_handlers"](application, handler_group)

    # let's go dude
    application.run_polling(bootstrap_retries=-1)


if __name__ == "__main__":
    main()
