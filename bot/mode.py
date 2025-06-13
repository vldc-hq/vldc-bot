import logging
from functools import wraps
from typing import Callable, List, Optional

# asyncio removed
from telegram import Update, Message
from telegram.error import TelegramError  # Import TelegramError
from telegram.ext import (
    Application,  # Updater changed to Application
    CommandHandler,
    CallbackContext,
    # Dispatcher, # Dispatcher is part of Application
    JobQueue,
)

# from telegram.ext.dispatcher import DEFAULT_GROUP # Removed

from filters import admin_filter
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

ON, OFF = True, False


class Mode:
    """Todo: add docstring (no)"""

    _dp: Application  # Dispatcher changed to Application
    _mode_handlers: List[CommandHandler] = []

    def __init__(
        self,
        mode_name: str,
        default: bool = True,
        pin_info_msg: bool = False,
        off_callback: Optional[
            Callable[[Application], None]
        ] = None,  # Dispatcher changed to Application
        on_callback: Optional[
            Callable[[Application], None]
        ] = None,  # Dispatcher changed to Application
    ) -> None:
        self.name = mode_name
        self.default = default
        self.chat_data_key = self._gen_chat_data_key(mode_name)
        self.pin_info_msg = pin_info_msg
        self.off_callback = off_callback
        self.on_callback = on_callback

        self.handlers_gr = Application.DEFAULT_GROUP  # Changed

    @staticmethod
    def _gen_chat_data_key(mode_name: str) -> str:
        return f"is_{mode_name}_on".lower()

    def _get_mode_state(self, context: CallbackContext):
        if self.chat_data_key not in context.chat_data:
            context.chat_data[self.chat_data_key] = self.default

        return context.chat_data[self.chat_data_key]

    def _set_mode(self, state: bool, context: CallbackContext):
        context.chat_data[self.chat_data_key] = state
        logger.info("new state: %s", state)
        if state is ON:
            self._add_mode_handlers()
        elif state is OFF:
            self._remove_mode_handlers()
        else:
            raise ValueError(f"wrong mode state. expect [True, False], got: {state}")

    def _add_on_off_handlers(self):
        self._dp.add_handler(
            ChatCommandHandler(
                f"{self.name}_on",
                self._mode_on,
                custom_filters=admin_filter,
            ),
            self.handlers_gr,
        )
        self._dp.add_handler(
            ChatCommandHandler(
                f"{self.name}_off",
                self._mode_off,
                custom_filters=admin_filter,
            ),
            self.handlers_gr,
        )
        self._dp.add_handler(
            ChatCommandHandler(f"{self.name}", self._mode_status),
            self.handlers_gr,
        )

    def _remove_mode_handlers(self):
        for h in self._mode_handlers:
            self._dp.remove_handler(h, self.handlers_gr)

    def _add_mode_handlers(self):
        for h in self._mode_handlers:
            self._dp.add_handler(h, self.handlers_gr)

    async def _mode_on(self, update: Update, context: CallbackContext):
        logger.info("%s switch to ON", self.name)
        mode = self._get_mode_state(context)
        if mode is OFF:
            self._set_mode(ON, context)

            if self.on_callback is not None:
                try:
                    # Assuming on_callback handles its own async execution if needed (e.g. asyncio.create_task)
                    self.on_callback(self._dp)
                except Exception as err:
                    logger.error("can't eval mode_on callback: %s", err)
                    raise err

            msg = await context.bot.send_message(
                update.effective_chat.id, f"{self.name} is ON"
            )
            if self.pin_info_msg is True:
                await context.bot.pin_chat_message(
                    update.effective_chat.id, msg.message_id, disable_notification=True
                )

    async def _mode_off(self, update: Update, context: CallbackContext):
        logger.info("%s switch to OFF", self.name)
        mode = self._get_mode_state(context)
        if mode is ON:
            self._set_mode(OFF, context)

            if self.off_callback is not None:
                try:
                    # Assuming off_callback handles its own async execution if needed
                    self.off_callback(self._dp)
                except Exception as err:
                    logger.error("can't eval mode_off callback: %s", err)
                    raise err

            await context.bot.send_message(
                update.effective_chat.id, f"{self.name} is OFF"
            )
            if self.pin_info_msg is True:
                await context.bot.unpin_chat_message(update.effective_chat.id)

    async def _mode_status(self, update: Update, context: CallbackContext):
        status = "ON" if self._get_mode_state(context) is ON else "OFF"
        logger.info("%s status is %s", self.name, status)
        await context.bot.send_message(
            update.effective_chat.id, f"{self.name} status is {status}"
        )  # msg variable removed, send original f-string

    def add(self, func) -> Callable:
        @wraps(func)
        def wrapper(
            app: Application, handlers_group: int
        ):  # upd: Updater to app: Application
            self._dp = app  # upd.dispatcher to app (Application is the dispatcher)
            self.handlers_gr = handlers_group

            logger.info("adding users handlers...")
            func(app, self.handlers_gr)  # upd to app

            # if mode doesn't define any handlers
            if (
                self.handlers_gr in app.handlers
            ):  # upd.dispatcher.handlers to app.handlers
                self._mode_handlers = app.handlers[
                    self.handlers_gr
                ].copy()  # upd.dispatcher.handlers to app.handlers
            logger.info(
                "registered %d %s handlers", len(self._mode_handlers), self.name
            )

            self._add_on_off_handlers()
            # todo:
            #  https://github.com/vldc-hq/vldc-bot/issues/104
            #  for some reason, if you don't put handlers remover here
            #  mods with default=True do not get _on | _off command handlers
            self._remove_mode_handlers()

            if self.default is True:
                self._add_mode_handlers()

        return wrapper


def cleanup_queue_update(
    queue: JobQueue,
    cmd: Optional[Message],
    result: Optional[Message],
    seconds: int,
    remove_cmd=True,
    remove_reply=False,
):
    _remove_message_after(result, queue, seconds)

    if remove_cmd and cmd:
        _remove_message_after(cmd, queue, seconds)

    if remove_reply and cmd and cmd.reply_to_message:  # type: ignore
        reply: Message = cmd.reply_to_message  # type: ignore
        _remove_message_after(reply, queue, seconds)


async def _actual_delete_job(context: CallbackContext):
    """Actual job function to delete the message."""
    msg_to_delete: Message = context.job.data
    try:
        await msg_to_delete.delete()
        logger.debug("Message %s deleted by job.", msg_to_delete.message_id)
    except TelegramError as e:  # Changed from Exception to TelegramError
        logger.error(
            "Failed to delete message %s by job (TelegramError): %s",
            msg_to_delete.message_id,
            e,
        )
    except (
        Exception  # pylint: disable=broad-except
    ) as e:  # Catch other potential errors
        logger.error(
            "Failed to delete message %s by job (OtherException): %s",
            msg_to_delete.message_id,
            e,
        )


def _remove_message_after(message: Message, job_queue: JobQueue, seconds: int):
    logger.debug(
        "Scheduling cleanup of message %s in %d seconds",
        message.message_id,  # Log message_id for brevity
        seconds,
    )
    job_queue.run_once(
        _actual_delete_job,
        seconds,
        data=message,
        name=f"delete_{message.chat_id}_{message.message_id}",
    )


__all__ = ["Mode", "cleanup_queue_update", "ON", "OFF"]
