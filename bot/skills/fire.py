import logging
import random

from telegram import Update, User
from telegram.ext import ContextTypes
from typing_utils import App, get_job_queue

from mode import cleanup_queue_update
from handlers import ChatCommandHandler

logger = logging.getLogger(__name__)

# Прилагательные в родительном падеже (мужской/средний род)
ADJECTIVES = [
    "систематического",
    "неконтролируемого",
    "демонстративного",
    "подозрительного",
    "хронического",
    "избыточного",
    "мистического",
    "несанкционированного",
    "громкого",
    "неприличного",
    "агрессивного",
    "таинственного",
    "виртуального",
    "философского",
    "пассивного",
    "драматического",
    "космического",
]

# Существительные в родительном падеже (мужской/средний род)
NOUNS = [
    "запаха",
    "поведения",
    "молчания",
    "дыхания",
    "взгляда",
    "кашля",
    "аппетита",
    "сна",
    "смеха",
    "везения",
    "нытья",
    "сидения",
    "присутствия",
    "интеллекта",
    "юмора",
    "обаяния",
    "игнорирования",
]


def generate_dismissal_reason() -> str:
    """Генерирует случайную и смешную причину увольнения."""
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    return f"по причине {adj} {noun}"


def add_fire(app: App, handlers_group: int):
    logger.info("registering fire handlers")
    app.add_handler(ChatCommandHandler("fire", fire), group=handlers_group)


async def fire(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.reply_to_message is None:
        return
    if update.effective_chat is None:
        return
    user: User | None = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    if user and chat_id:
        reason = " ".join(context.args or []).strip()
        if not reason:
            reason = generate_dismissal_reason()
        result = await context.bot.send_message(
            chat_id, f"Пользователь {user.name} уволен {reason}"
        )
        cleanup_queue_update(
            get_job_queue(context),
            update.message,
            result,
            600,
            remove_cmd=True,
            remove_reply=False,
        )
