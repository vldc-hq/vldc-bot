import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, run_async

from filters import admin_filter

logger = logging.getLogger(__name__)

ON, OFF = True, False


class Mode:
    def __init__(self, mode_name: str, default: bool = True, pin_info_msg: bool = False) -> None:
        self.name = mode_name
        self.default = default
        self.chat_data_key = self._gen_chat_data_key(mode_name)
        self.pin_info_msg = pin_info_msg

    @staticmethod
    def _gen_chat_data_key(mode_name: str) -> str:
        return f"is_{mode_name}_on".lower()

    def _get_mode_state(self, context: CallbackContext):
        if self.chat_data_key not in context.chat_data:
            context.chat_data[self.chat_data_key] = self.default

        return context.chat_data[self.chat_data_key]

    def _set_mode(self, state: bool, context: CallbackContext):
        context.chat_data[self.chat_data_key] = state

    def add(self, func) -> Callable:
        @wraps(func)
        def wrapper(upd: Updater, handlers_group: int):
            dp = upd.dispatcher
            dp.add_handler(CommandHandler(f"{self.name}_on", self.mode_on, filters=admin_filter), handlers_group)
            dp.add_handler(CommandHandler(f"{self.name}_on", self.mode_off, filters=admin_filter), handlers_group)
            func(upd, handlers_group)

        return wrapper

    @run_async
    def handler(self, func) -> Callable:
        @wraps(func)
        def wrapper(update: Update, context: CallbackContext):
            mode_is_on = self._get_mode_state(context)
            if mode_is_on:
                func(update, context)

        return wrapper

    @run_async
    def mode_on(self, update: Update, context: CallbackContext):
        logger.info(f"{self.name} switch to ON")
        mode = self._get_mode_state(context)
        if mode is OFF:
            msg = context.bot.send_message(update.effective_chat.id, f"{self.name} is ON 🙊")
            if self.pin_info_msg is True:
                context.bot.pin_chat_message(
                    update.effective_chat.id,
                    msg.message_id,
                    disable_notification=True
                )
            self._set_mode(ON, context)

    @run_async
    def mode_off(self, update: Update, context: CallbackContext):
        logger.info(f"{self.name} switch to OFF")
        mode = self._get_mode_state(context)
        if mode is ON:
            context.bot.send_message(update.effective_chat.id, f"{self.name} is OFF 🙊")
            if self.pin_info_msg is True:
                context.bot.unpin_chat_message(update.effective_chat.id)
            self._set_mode(OFF, context)


__all__ = ["Mode"]
