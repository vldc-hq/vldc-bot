from telegram.ext import BaseFilter
from telegram import Message
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
            return bool(re.search(r'\bu[wv]+u\b', message.text, re.IGNORECASE))

        return False

class OnlyAdminOnOthersFilter(BaseFilter):
    """ Messages only from admins with reply """
    name = 'Filters.onlyAdminOnOthers'

    def filter(self, message: Message) -> bool:
        if message.reply_to_message != None:
            return message.from_user.id in {
                a.user.id for a in message.chat.get_administrators()
            }
        else:
            return True

admin_filter = AdminFilter()
uwu_filter = UwuFilter()
only_admin_on_others = OnlyAdminOnOthersFilter()