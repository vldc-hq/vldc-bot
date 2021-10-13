import re

from telegram import Message
from telegram.ext import MessageFilter

from config import get_debug


class AdminFilter(MessageFilter):
    """Messages only from admins"""

    name = "Filters.admin"

    def filter(self, message) -> bool:
        return message.from_user.id in {
            a.user.id for a in message.chat.get_administrators()
        }


class UwuFilter(MessageFilter):
    """Regexp check for UwU"""

    name = "Filters.uwu"

    def filter(self, message) -> bool:
        if message.text:
            return bool(re.search(r"\bu[wv]+u\b", message.text, re.IGNORECASE))

        return False


class OnlyAdminOnOthersFilter(MessageFilter):
    """Messages only from admins with reply"""

    name = "Filters.onlyAdminOnOthers"

    def filter(self, message: Message) -> bool:
        if get_debug():
            return True
        if message.reply_to_message is not None:
            return message.from_user.id in {
                a.user.id for a in message.chat.get_administrators()
            }

        return True


admin_filter = AdminFilter()
uwu_filter = UwuFilter()
only_admin_on_others = OnlyAdminOnOthersFilter()
