from functools import wraps
from telegram import Message, Bot
from telegram.ext import CallbackContext

import logging

logger = logging.getLogger(__name__)


def _hook_message(bot: Bot, callback_after=lambda x: x):
    orig_fn = getattr(bot, '_message')

    def wrapped_fn(*args, **kwargs):
        result = orig_fn(*args, **kwargs)
        callback_after(result)
    setattr(bot, '_message', wrapped_fn)


def _remove_message_after(message: Message, context: CallbackContext,
                          seconds: int):
    logger.debug(f'''Scheduling cleanup of message {message.message_id}
                 in {seconds} seconds''')
    context.job_queue.run_once(lambda _: message.delete(), seconds,
                               context=message.chat_id)


def cleanup(seconds: int):
    """Remove messages emitted by decorated function"""
    logger.debug(f"Removing message from bot in {seconds}")

    def cleanup_decorator(func):
        logger.debug(func)
        @wraps(func)
        def cleanup_wrapper(*args, **kwargs):
            for arg in args:
                if isinstance(arg, CallbackContext):
                    _hook_message(arg.bot, lambda msg:
                                  _remove_message_after(msg, arg, seconds))

            return func(*args, **kwargs)
        return cleanup_wrapper
    return cleanup_decorator
