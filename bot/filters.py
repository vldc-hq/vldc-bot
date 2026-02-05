import re
from typing import Optional, Union, Any

from pymongo.collection import Collection
from telegram import Message
from telegram.ext.filters import MessageFilter

from config import get_debug
from db.mongo import get_db


class TrustedDB:
    def __init__(self, db_name: str):
        self._coll: Collection[dict[str, Any]] = get_db(db_name).users

    def is_trusted(self, user_id: int | str) -> bool:
        return self._coll.find_one({"_id": user_id}) is not None


_trusted_db = TrustedDB("trusted")


class TrustedFilter(MessageFilter):
    """Messages only from trusted users"""

    @property
    def name(self) -> str:
        return "Filter.trusted"

    @name.setter
    def name(self, name: str) -> None:
        del name

    def filter(self, message: Message) -> Optional[Union[bool, dict[str, Any]]]:
        if get_debug():
            return True
        if message.from_user is None:
            return None
        return _trusted_db.is_trusted(message.from_user.id)


class UwuFilter(MessageFilter):
    """Regexp check for UwU"""

    @property
    def name(self) -> str:
        return "Filters.uwu"

    @name.setter
    def name(self, name: str) -> None:
        del name

    def filter(self, message: Message) -> bool:
        if message.text:
            return bool(re.search(r"\bu[wv]+u\b", message.text, re.IGNORECASE))

        return False


uwu_filter = UwuFilter()
trusted_filter = TrustedFilter()
