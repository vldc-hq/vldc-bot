import logging
import os
from typing import Callable

from google.cloud import translate
from telegram import Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

from mode import Mode, OFF

logger = logging.getLogger(__name__)

mode = Mode(mode_name="fools_mode", default=OFF)


@mode.add
def add_fools_mode(upd: Updater, handlers_group: int):
    logger.info("registering fools handlers")
    dp = upd.dispatcher

    dp.add_handler(MessageHandler(Filters.group & ~
    Filters.status_update, mesaĝa_traduko, run_async=True), handlers_group)


def mesaĝa_traduko(update: Update, context: CallbackContext):
    text = update.message['text']
    user: User = update.effective_user
    chat_id = update.effective_chat.id

    try:
        context.bot.delete_message(
            chat_id, update.effective_message.message_id)
    except (BadRequest, TelegramError) as err:
        logger.info("can't delete msg: %s", err)

    # akiri avataron kaj lingvon por uzanto kiel Jedajo
    magia_nombro = sum([ord(c) for c in user.full_name])
    lingvoj = ['ro', 'uk', 'sr', 'sk', 'sl', 'uz', 'bg', 'mn', 'kk']
    lingvo = lingvoj[magia_nombro % len(lingvoj)]
    emoji = chr(ord('😀') + magia_nombro % 75)
    if user.name == "@KittyHawk1":
        lingvo = "he"
        emoji = "🧘‍♂️"
    try:
        context.bot.send_message(
            chat_id, f"{emoji} {user.full_name}: {traduki(text, lingvo)}")
    except TelegramError as err:
        logger.info("can't translate msg: %s, because of: %s", text, err)


def f(text: str, lingvo: str) -> str:
    project_id = os.getenv("GOOGLE_PROJECT_ID")

    client = translate.TranslationServiceClient()

    parent = client.common_location_path(project_id, "global")

    response = client.translate_text(
        parent=parent,
        contents=[text],
        mime_type="text/plain",
        source_language_code="ru",
        target_language_code=lingvo,
    )

    return response.translations[0].translated_text


def _make_traduki(func: Callable[[str, str], str]) -> Callable[[str, str], str]:
    def tr(string: str, lang: str) -> str:
        if string is None or len(string) < 1:
            raise ValueError("nothing to translate")
        return func(string, lang)

    return tr


traduki = _make_traduki(f)
