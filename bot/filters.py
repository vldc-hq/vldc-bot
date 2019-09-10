from telegram.ext import BaseFilter


class AdminFilter(BaseFilter):
    """ Messages only from admins """
    name = 'Filters.admin'

    def filter(self, message) -> bool:
        return message.from_user.id in {
            a.user.id for a in message.chat.get_administrators()
        }
