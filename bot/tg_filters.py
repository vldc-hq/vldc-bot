import logging

from telegram.ext import filters

from config import get_group_chat_id

logger = logging.getLogger(__name__)


def group_chat_filter():
    chat_id_or_name = get_group_chat_id()
    if not chat_id_or_name:
        logger.warning("CHAT_ID is empty; group filter disabled")
        return filters.ALL

    try:
        return filters.Chat(chat_id=int(chat_id_or_name))
    except ValueError:
        return filters.Chat(username=chat_id_or_name.strip("@"))
