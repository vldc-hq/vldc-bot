import logging
from typing import Set

from telegram import Update
from telegram.constants import ChatMemberStatus, ChatType
from telegram.error import TelegramError
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


ADMIN_STATUSES: Set[str] = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}


async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return False

    if chat.type == ChatType.PRIVATE:
        return True

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
    except TelegramError as err:  # pragma: no cover - defensive
        logger.warning("admin check failed: %s", err)
        return False

    return member.status in ADMIN_STATUSES
