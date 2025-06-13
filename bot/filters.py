import re
from typing import Optional, Union

from pymongo.collection import Collection
from telegram import Message
from telegram.ext import filters  # MessageFilter removed, filters is already imported
from telegram.ext.filters import (
    DataDict,
)  # This might need to be telegram.ext.filters.DataDict if not available directly

from config import get_debug
from db.mongo import get_db


class TrustedDB:
    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).users

    def is_trusted(self, user_id: str) -> bool:
        return self._coll.find_one({"_id": user_id}) is not None


_trusted_db = TrustedDB("trusted")


class TrustedFilter(filters.BaseFilter):  # Changed MessageFilter to filters.BaseFilter
    """Messages only from trusted users"""

    name = "Filter.trusted"  # Keep name for now, may need review

    def filter(self, message: Message) -> Optional[Union[bool, DataDict]]:
        if get_debug():
            return True
        return _trusted_db.is_trusted(message.from_user.id)


class AdminFilter(filters.BaseFilter):  # Changed MessageFilter to filters.BaseFilter
    """Messages only from admins"""

    name = "Filters.admin"  # Keep name for now

    def filter(self, message) -> bool:  # Type hint for message can be Message
        if get_debug():
            return True
        # Ensure message has 'from_user' and 'chat' attributes as expected
        if (
            hasattr(message, "from_user")
            and message.from_user
            and hasattr(message, "chat")
        ):
            return message.from_user.id in {
                a.user.id for a in message.chat.get_administrators()
            }
        return False


class UwuFilter(filters.BaseFilter):  # Changed MessageFilter to filters.BaseFilter
    """Regexp check for UwU"""

    name = "Filters.uwu"  # Keep name for now

    def filter(self, message: Message) -> bool:  # Added type hint for message
        if message.text:
            return bool(re.search(r"\bu[wv]+u\b", message.text, re.IGNORECASE))

        return False


class OnlyAdminOnOthersFilter(
    filters.BaseFilter
):  # Changed MessageFilter to filters.BaseFilter
    """Messages only from admins with reply"""

    name = "Filters.onlyAdminOnOthers"  # Keep name for now

    def filter(self, message: Message) -> bool:
        if get_debug():
            return True
        if message.reply_to_message is not None:
            # Ensure message has 'from_user' and 'chat' attributes
            if (
                hasattr(message, "from_user")
                and message.from_user
                and hasattr(message, "chat")
            ):
                return message.from_user.id in {
                    a.user.id for a in message.chat.get_administrators()
                }
            return False  # Or handle as an error/log

        return True


admin_filter = AdminFilter()
uwu_filter = UwuFilter()
only_admin_on_others = OnlyAdminOnOthersFilter()
trusted_filter = TrustedFilter()
