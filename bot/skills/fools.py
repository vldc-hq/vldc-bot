import logging
import os
from typing import Any, Callable, cast
from telegram import Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import MessageHandler, ContextTypes, filters

from tg_filters import group_chat_filter
from mode import Mode, OFF
from typing_utils import App

logger = logging.getLogger(__name__)

try:
    from google.cloud import translate
except Exception as exc:  # pylint: disable=broad-except
    translate = None
    logger.warning("google translate unavailable; fools mode disabled: %s", exc)

mode = Mode(mode_name="fools_mode", default=OFF)


@mode.add
def add_fools_mode(app: App, handlers_group: int):
    if translate is None:
        logger.warning("fools mode disabled: google translate not available")
        return
    logger.info("registering fools handlers")

    group_filter = group_chat_filter()
    app.add_handler(
        MessageHandler(
            ~filters.StatusUpdate.ALL & group_filter,
            mesaĝa_traduko,
            block=False,
        ),
        group=handlers_group,
    )


async def mesaĝa_traduko(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.effective_chat is None:
        return
    message = update.message
    text = message.text or ""
    user: User | None = update.effective_user
    if user is None:
        return
    chat_id = update.effective_chat.id

    try:
        await context.bot.delete_message(chat_id, message.message_id)
    except (BadRequest, TelegramError) as err:
        logger.info("can't delete msg: %s", err)

    # akiri avataron kaj lingvon por uzanto kiel Jedajo
    magia_nombro = sum([ord(c) for c in user.full_name])
    lingvoj = ["ro", "uk", "sr", "sk", "sl", "uz", "bg", "mn", "kk"]
    lingvo = lingvoj[magia_nombro % len(lingvoj)]
    emoji = chr(ord("😀") + magia_nombro % 75)
    if user.name == "@KittyHawk1":
        lingvo = "he"
        emoji = "🧘‍♂️"
    try:
        translated = traduki(text, lingvo)
    except Exception as err:  # pylint: disable=broad-except
        logger.warning("translation failed, sending original: %s", err)
        translated = text
    try:
        await context.bot.send_message(
            chat_id, f"{emoji} {user.full_name}: {translated}"
        )
    except TelegramError as err:
        logger.info("can't translate msg: %s, because of: %s", text, err)


def f(text: str, lingvo: str) -> str:
    if translate is None:
        raise RuntimeError("google translate is not available")
    project_id = os.getenv("GOOGLE_PROJECT_ID")
    if not project_id:
        raise RuntimeError("GOOGLE_PROJECT_ID is not set")

    client = cast(Any, translate.TranslationServiceClient())

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
        if len(string) < 1:
            raise ValueError("nothing to translate")
        return func(string, lang)

    return tr


traduki = _make_traduki(f)
