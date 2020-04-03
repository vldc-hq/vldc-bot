import logging
from functools import wraps
from typing import Callable, List, Optional

from telegram import Update, Bot, Message
from telegram.ext import (Updater, CommandHandler, CallbackContext, run_async,
                          Dispatcher, JobQueue)
from telegram.ext.dispatcher import DEFAULT_GROUP

from filters import admin_filter

logger = logging.getLogger(__name__)

ON, OFF = True, False


class Mode:
    """ Todo: add docstring (no) """
    _dp: Dispatcher
    _mode_handlers: List[CommandHandler] = []

    def __init__(
            self,
            mode_name: str,
            default: bool = True,
            pin_info_msg: bool = False,
            off_callback: Optional[Callable[[Dispatcher], None]] = None,
            on_callback: Optional[Callable[[Dispatcher], None]] = None) -> None:
        self.name = mode_name
        self.default = default
        self.chat_data_key = self._gen_chat_data_key(mode_name)
        self.pin_info_msg = pin_info_msg
        self.off_callback = off_callback
        self.on_callback = on_callback

        self.handlers_gr = DEFAULT_GROUP

    @staticmethod
    def _gen_chat_data_key(mode_name: str) -> str:
        return f"is_{mode_name}_on".lower()

    def _get_mode_state(self, context: CallbackContext):
        if self.chat_data_key not in context.chat_data:
            context.chat_data[self.chat_data_key] = self.default

        return context.chat_data[self.chat_data_key]

    def _set_mode(self, state: bool, context: CallbackContext):
        context.chat_data[self.chat_data_key] = state
        logger.info(f"new state: {state}")
        if state is ON:
            self._add_mode_handlers()
        elif state is OFF:
            self._remove_mode_handlers()
        else:
            raise ValueError(f"wrong mode state. expect [True, False], got: {state}")

    def _add_on_off_handlers(self):
        self._dp.add_handler(CommandHandler(f"{self.name}_on", self._mode_on, filters=admin_filter), self.handlers_gr)
        self._dp.add_handler(CommandHandler(f"{self.name}_off", self._mode_off, filters=admin_filter), self.handlers_gr)
        self._dp.add_handler(CommandHandler(f"{self.name}", self._mode_status), self.handlers_gr)

    def _remove_mode_handlers(self):
        for h in self._mode_handlers:
            self._dp.remove_handler(h, self.handlers_gr)

    def _add_mode_handlers(self):
        for h in self._mode_handlers:
            self._dp.add_handler(h, self.handlers_gr)

    @run_async
    def _mode_on(self, update: Update, context: CallbackContext):
        logger.info(f"{self.name} switch to ON")
        mode = self._get_mode_state(context)
        if mode is OFF:
            self._set_mode(ON, context)

            if self.on_callback is not None:
                try:
                    self.on_callback(self._dp)
                except Exception as err:
                    logger.error(f"can't eval mode_on callback: {err}")
                    raise err

            msg = context.bot.send_message(update.effective_chat.id, f"{self.name} is ON")
            if self.pin_info_msg is True:
                context.bot.pin_chat_message(update.effective_chat.id, msg.message_id, disable_notification=True)

    @run_async
    def _mode_off(self, update: Update, context: CallbackContext):
        logger.info(f"{self.name} switch to OFF")
        mode = self._get_mode_state(context)
        if mode is ON:
            self._set_mode(OFF, context)

            if self.off_callback is not None:
                try:
                    self.off_callback(self._dp)
                except Exception as err:
                    logger.error(f"can't eval mode_off callback: {err}")
                    raise err

            context.bot.send_message(update.effective_chat.id, f"{self.name} is OFF")
            if self.pin_info_msg is True:
                context.bot.unpin_chat_message(update.effective_chat.id)

    @run_async
    def _mode_status(self, update: Update, context: CallbackContext):
        status = "ON" if self._get_mode_state(context) is ON else "OFF"
        msg = f"{self.name} status is {status}"
        logger.info(msg)
        context.bot.send_message(update.effective_chat.id, msg)

    def add(self, func) -> Callable:
        @wraps(func)
        def wrapper(upd: Updater, handlers_group: int):
            self._dp = upd.dispatcher
            self.handlers_gr = handlers_group

            logger.info(f"adding users handlers...")
            func(upd, self.handlers_gr)

            self._mode_handlers = upd.dispatcher.handlers[self.handlers_gr].copy()
            logger.info(f"registered {len(self._mode_handlers)} {self.name} handlers")

            self._add_on_off_handlers()
            # todo:
            #  https://github.com/egregors/vldc-bot/issues/104
            #  for some reason, if you don't put handlers remover here
            #  mods with default=True do not get _on | _off command handlers
            self._remove_mode_handlers()

            if self.default is True:
                self._add_mode_handlers()

        return wrapper


# https://github.com/egregors/vldc-bot/issues/72
def _hook_message(bot: Bot, callback_after=lambda x: x):
    orig_fn = getattr(bot, '_message')

    def wrapped_fn(*args, **kwargs):
        result = orig_fn(*args, **kwargs)
        callback_after(result)
        return result

    setattr(bot, '_message', wrapped_fn)
    return orig_fn


@run_async
def _remove_message_after(message: Message, job_queue: JobQueue, seconds: int):
    logger.debug(f"Scheduling cleanup of message {message} \
                   in {seconds} seconds")
    job_queue.run_once(lambda _: message.delete(), seconds,
                       context=message.chat_id)


def cleanup_inner_wrapper(seconds:int, remove_cmd, remove_reply,
                          args, kwargs, func,
                          bot: Bot, queue: JobQueue, message: Optional[Message]):
    # Hook message method on Bot
    # So everything after that will be catched
    # And also removed
    orig_fn = _hook_message(bot, lambda msg: (
        _remove_message_after(msg, queue, seconds)
    ))

    if message:
        if remove_cmd:
            _remove_message_after(message, queue, seconds)
        if remove_reply and message.reply_to_message:  # type: ignore
            reply: Message = message.reply_to_message  # type: ignore
            _remove_message_after(reply, queue, seconds)
    
    result = None
    
    try:
        result = func(*args, **kwargs)
    except Exception as err:
        logger.error(str(err))
    setattr(bot, '_message', orig_fn)
    return result


def cleanup_update_context(seconds: int, remove_cmd=True, remove_reply=False):
    """Cleanup decorator for Update, CallbackContext
    Remove messages emitted by decorated function with arguments Update, CallbackContext

    Args:
        seconds (:obj:`int`): Amount of seconds after which message should be deleted
        remove_cmd (:obj:`bool`, optional): Whether user command should be deleted, default True
        remove_reply (:obj:`bool`, optional): Whether reply should be deleted

    """
    logger.debug(f"Removing message from bot in {seconds}")

    def cleanup_decorator(func):
        logger.debug(f"cleanup_decorator func: {func}")

        @wraps(func)
        def cleanup_wrapper(*args, **kwargs):
            update: Update = args[0]
            context: CallbackContext = args[1]

            queue: JobQueue = context.job_queue

            bot: Bot = context.bot
            message: Message = update.message

            return cleanup_inner_wrapper(seconds, remove_cmd, remove_reply, args, 
                                         kwargs, func, bot, queue, message)

        return cleanup_wrapper

    return cleanup_decorator


def cleanup_bot_queue(seconds: int):
    """Cleanup decorator for Bot, JobQueue
    Remove messages emitted by decorated function with arguments Bot, JobQueue

    Args:
        seconds (:obj:`int`): Amount of seconds after which message should be deleted
    """
    logger.debug(f"Removing message from bot in {seconds}")

    def cleanup_decorator(func):
        logger.debug(f"cleanup_decorator func: {func}")

        @wraps(func)
        def cleanup_wrapper(*args, **kwargs):
            bot: Bot = args[0]
            queue: JobQueue = args[1]

            return cleanup_inner_wrapper(seconds, False, False, args, 
                                         kwargs, func, bot, queue, None)

        return cleanup_wrapper

    return cleanup_decorator



__all__ = ["Mode", "cleanup_bot_queue", "cleanup_update_context", "ON", "OFF"]
