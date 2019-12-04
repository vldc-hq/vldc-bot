from functools import wraps
from telegram import Message
from telegram.ext import CallbackContext

import logging

logger = logging.getLogger(__name__)


def _hook_function(obj, func_name, callback_before=None, callback_after=None):
    logger.debug(f"Hooking {func_name}")
    orig_fn = getattr(obj, func_name)

    def wrapped_fn(*args, **kwargs):
        callback_before(*args, **kwargs)
        result = orig_fn(*args, **kwargs)
        callback_after(result, *args, **kwargs)
        return result
    setattr(obj, func_name, wrapped_fn)


def _remove_Message_after_timer(message: Message, context: CallbackContext,
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
                    _hook_function(arg.bot, '_message',
                                   lambda *args, **kwargs: 1,
                                   lambda msg, *args, **kwargs:
                                   (_remove_Message_after_timer(msg, arg,
                                    seconds)))

            return func(*args, **kwargs)
        return cleanup_wrapper
    return cleanup_decorator
