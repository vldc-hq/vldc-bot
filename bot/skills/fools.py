import logging
import os
from typing import Callable
from telegram import Update, User
from telegram.error import BadRequest, TelegramError
from telegram.ext import Application, MessageHandler, ContextTypes, filters

from tg_filters import group_chat_filter
from mode import Mode, OFF

logger = logging.getLogger(__name__)

try:
    from google.cloud import translate
except Exception as exc:  # pylint: disable=broad-except
    translate = None
    logger.warning("google translate unavailable; fools mode disabled: %s", exc)

mode = Mode(mode_name="fools_mode", default=OFF)


@mode.add
def add_fools_mode(app: Application, handlers_group: int):
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
    text = update.message["text"]
    user: User = update.effective_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.delete_message(chat_id, update.effective_message.message_id)
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
        await context.bot.send_message(
            chat_id, f"{emoji} {user.full_name}: {traduki(text, lingvo)}"
        )
    except TelegramError as err:
        logger.info("can't translate msg: %s, because of: %s", text, err)


def f(text: str, lingvo: str) -> str:
    if translate is None:
        raise RuntimeError("google translate is not available")
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
