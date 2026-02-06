import logging
from functools import wraps
from typing import Callable, List, Optional

from telegram import Update, Message
from telegram.error import BadRequest, NetworkError, TimedOut, TelegramError
from telegram.ext import (
    ContextTypes,
)

from handlers import ChatCommandHandler
from typing_utils import App, JobQueueT, BaseHandlerT

logger = logging.getLogger(__name__)

ON, OFF = True, False
DEFAULT_GROUP = 0


class Mode:
    """Todo: add docstring (no)"""

    _dp: App
    _mode_handlers: List[BaseHandlerT] = []

    def __init__(
        self,
        mode_name: str,
        default: bool = True,
        *,
        pin_info_msg: bool = False,
        off_callback: Optional[Callable[[App], None]] = None,
        on_callback: Optional[Callable[[App], None]] = None,
    ) -> None:
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

    def _get_mode_state(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        chat_data = context.chat_data
        if chat_data is None:
            return self.default
        if self.chat_data_key not in chat_data:
            chat_data[self.chat_data_key] = self.default

        return chat_data[self.chat_data_key]

    def _set_mode(self, state: bool, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_data = context.chat_data
        if chat_data is None:
            return
        chat_data[self.chat_data_key] = state
        logger.info("new state: %s", state)
        if state is ON:
            self._add_mode_handlers()
        elif state is OFF:
            self._remove_mode_handlers()
        else:
            raise ValueError(f"wrong mode state. expect [True, False], got: {state}")

    def _add_on_off_handlers(self) -> None:
        self._dp.add_handler(
            ChatCommandHandler(
                f"{self.name}_on",
                self._mode_on,
                require_admin=True,
            ),
            self.handlers_gr,
        )
        self._dp.add_handler(
            ChatCommandHandler(
                f"{self.name}_off",
                self._mode_off,
                require_admin=True,
            ),
            self.handlers_gr,
        )
        self._dp.add_handler(
            ChatCommandHandler(f"{self.name}", self._mode_status),
            self.handlers_gr,
        )

    def _remove_mode_handlers(self) -> None:
        for h in self._mode_handlers:
            self._dp.remove_handler(h, self.handlers_gr)

    def _add_mode_handlers(self) -> None:
        for h in self._mode_handlers:
            self._dp.add_handler(h, self.handlers_gr)

    async def _mode_on(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        logger.info("%s switch to ON", self.name)
        mode = self._get_mode_state(context)
        if mode is OFF:
            self._set_mode(ON, context)

            if self.on_callback is not None:
                try:
                    self.on_callback(self._dp)
                except Exception as err:
                    logger.error("can't eval mode_on callback: %s", err)
                    raise err

            chat = update.effective_chat
            if chat is None:
                return
            msg = await context.bot.send_message(chat.id, f"{self.name} is ON")
            if self.pin_info_msg is True:
                await context.bot.pin_chat_message(
                    chat.id, msg.message_id, disable_notification=True
                )

    async def _mode_off(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        logger.info("%s switch to OFF", self.name)
        mode = self._get_mode_state(context)
        if mode is ON:
            self._set_mode(OFF, context)

            if self.off_callback is not None:
                try:
                    self.off_callback(self._dp)
                except Exception as err:
                    logger.error("can't eval mode_off callback: %s", err)
                    raise err

            chat = update.effective_chat
            if chat is None:
                return
            await context.bot.send_message(chat.id, f"{self.name} is OFF")
            if self.pin_info_msg is True:
                await context.bot.unpin_chat_message(chat.id)

    async def _mode_status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        status = "ON" if self._get_mode_state(context) is ON else "OFF"
        msg = f"{self.name} status is {status}"
        logger.info(msg)
        chat = update.effective_chat
        if chat is None:
            return
        await context.bot.send_message(chat.id, msg)

    def add(self, func: Callable[[App, int], None]) -> Callable[[App, int], None]:
        @wraps(func)
        def wrapper(app: App, handlers_group: int) -> None:
            self._dp = app
            self.handlers_gr = handlers_group

            logger.info("adding users handlers...")
            func(app, self.handlers_gr)

            # if mode doesn't define any handlers
            if self.handlers_gr in app.handlers:
                self._mode_handlers = app.handlers[self.handlers_gr].copy()
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
    queue: JobQueueT | None,
    cmd: Optional[Message],
    result: Optional[Message],
    seconds: int,
    *,
    remove_cmd: bool = True,
    remove_reply: bool = False,
):
    if queue is None:
        return
    _remove_message_after(result, queue, seconds)

    if remove_cmd and cmd:
        _remove_message_after(cmd, queue, seconds)

    if remove_reply and cmd and cmd.reply_to_message:  # type: ignore
        reply: Message = cmd.reply_to_message  # type: ignore
        _remove_message_after(reply, queue, seconds)


def _remove_message_after(
    message: Message | None, job_queue: JobQueueT, seconds: int
) -> None:
    logger.debug(
        "Scheduling cleanup of message %s \
                   in %d seconds",
        message,
        seconds,
    )

    async def _delete_message_job(context: ContextTypes.DEFAULT_TYPE) -> None:
        if message is None:
            return
        try:
            await context.bot.delete_message(
                chat_id=message.chat_id,
                message_id=message.message_id,
            )
        except (BadRequest, TimedOut, NetworkError, TelegramError) as exc:
            logger.info("skip message cleanup: %s", exc)

    job_queue.run_once(_delete_message_job, seconds, data=message)


__all__ = ["Mode", "cleanup_queue_update", "ON", "OFF"]
