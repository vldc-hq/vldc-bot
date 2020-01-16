from telegram.ext import BaseFilter
import re


class AdminFilter(BaseFilter):
    """ Messages only from admins """
    name = 'Filters.admin'

    def filter(self, message) -> bool:
        return message.from_user.id in {
            a.user.id for a in message.chat.get_administrators()
        }


class UwuFilter(BaseFilter):
    """ Regexp check for UwU """
    name = 'Filters.uwu'

    def filter(self, message) -> bool:
        if message.text:
            return bool(re.search(r'u(w+|v+)u', message.text, re.IGNORECASE))

        return False


admin_filter = AdminFilter()
uwu_filter = UwuFilter()
