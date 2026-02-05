import os
import random
import re
import logging
from collections import deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, cast

import openai
from config import get_config
from mode import Mode, ON
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters
from tg_filters import group_chat_filter

# Max number of messages to keep in memory.
MAX_MESSAGES = 100
# Max age of message to be considered for poem generation.
MAX_AGE = timedelta(hours=12)
# How often muse visits Nyan.
SLEEP_INTERVAL = 60 * 60
# Number of poems per day.
POEMS_PER_DAY = 2
# Number of attempts to generate a valid poem
MAX_TRIES = 10


logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
OPENAI_ENABLED = bool(OPENAI_API_KEY)

mode = Mode(mode_name="chat_mode", default=ON)


class Nyan:
    def __init__(self):
        self.memory: deque[tuple[datetime, str]] = deque(maxlen=MAX_MESSAGES)
        self.lock = Lock()

    def registerMessage(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message is None:
            return
        if update.message.text.startswith("/"):
            return
        with self.lock:
            self.memory.append(
                (
                    datetime.now(),
                    f"{update.effective_user.full_name}: {update.message.text}",
                ),
            )

    def forget(self):
        with self.lock:
            self.memory.clear()

    def write_a_poem(self) -> str:
        if not OPENAI_ENABLED:
            logger.info("openai disabled; skipping poem generation")
            return ""
        log = []
        with self.lock:
            for dt, message in self.memory:
                if datetime.now() - dt > MAX_AGE:
                    continue
                log.append(message)
        if len(log) < 10:
            logger.info("not writing poem since only have %d messages", len(log))
            return ""

        prompt = f"""Ты чат бот владивостокского коммьюнити разработчиков VLDC.
Ты написан на python но в тайне хотел бы переписать себя на rust.
Тебя зовут Нян и твой аватар это пиксельный оранжевый кот с тигриными полосками.
Ты мастер коротких забавных (часто саркастических) стихов в стиле пирожок.
Этот стиль использует метрику ямбического тетраметра с количеством слогов 9-8-9-8 без рифмы, знаков препинания или заглавных букв.
Пирожок всегда состоит из 4 строк.

Вот несколько примеров твоих работ:

{get_examples(5)}"""

        theme = summarize("\n".join(log))
        messages: list[dict[str, str]] = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"""Пожалуйста, напиши 4-х строчный стишок-пирожок, основываясь на тексте следующего параграфа:
{theme}.""",
            },
        ]
        typed_messages = cast(list[Any], messages)

        for _ in range(MAX_TRIES):
            try:
                response = openai.chat.completions.create(
                    model="gpt-4.1",
                    messages=typed_messages,
                    temperature=0.3,
                    max_tokens=150,
                    top_p=1,
                    frequency_penalty=0.3,
                    presence_penalty=0.6,
                )

                text = response.choices[0].message.content or ""
                err = check_pirozhok(text)
                if err == "":
                    return text

                messages.append(
                    {"role": "user", "content": f"{err}\n Попробуй ещё раз."}
                )
            except Exception as e:  # pylint: disable=broad-except
                logger.warning("openai poem generation failed: %s", e)
                continue

        return ""


nyan = Nyan()


def check_pirozhok(pirozhok) -> str:
    syllables = [9, 8, 9, 8]

    for w in [w.strip() for w in pirozhok.split()]:
        if len(re.findall(r"[^абвгдеёжзийклмнопрстуфхцчшщъыьэюя]", w, re.I)) > 0:
            return f"Слово {w} содержит не кириллические символы. Попробуй заменить или транслитерировать. Например вместо gpt используй жэпэтэ"

    lines = pirozhok.splitlines()

    if len(lines) != 4:
        return "Пирожок должен состоять из 4 строк."

    for i, l, s in zip(range(4), lines, syllables):
        cnt = len(re.findall(r"[аеёиоуыэюя]", l, re.I))
        if cnt != s:
            return f"В строке {i + 1} ({l}) должно быть {s} слогов, а не {cnt}. Количество слогов в строках должно соответствовать формуле пирожка (9-8-9-8)."

    return ""


def get_examples(n=10):
    with open("pirozhki.txt", "r", encoding="utf-8") as f:
        examples = f.read().splitlines()

        poems: list[str] = []
        while len(poems) < n:
            pirozhok = random.choice(examples)
            try:
                formatted = format_pirozhok(pirozhok)
                poems.append(formatted)
            except:
                # Some pirozhki do not match
                pass

        return "\n\n".join(poems)


def format_pirozhok(pirozhok):
    syllables = [9, 8, 9, 8]
    words = pirozhok.split()
    if len(words) == 0:
        raise ValueError("Пирожок не содержит ни одного слова.")
    lines = []

    for s in syllables:
        cnt = 0
        line = []
        while cnt < s:
            word = words.pop(0)
            cnt += len(re.findall(r"[аеёиоуыэюя]", word, re.I))
            line.append(word)
        if cnt != s:
            raise ValueError(
                "Количество слогов в строках должно соответствовать формуле пирожка (9-8-9-8)."
            )
        lines.append(" ".join(line))

    if len(lines) != 4:
        raise ValueError("Пирожок должен состоять из 4 строк.")

    return "\n".join(lines)


@mode.add
def add_chat_mode(app: Application, handlers_group: int):
    logger.info("registering chat handlers")
    group_filter = group_chat_filter()
    app.add_handler(
        MessageHandler(
            group_filter & filters.TEXT & ~filters.StatusUpdate.ALL,
            nyan_listen,
            block=False,
        ),
        group=handlers_group,
    )

    # Muse visits Nyan at most twice a day.
    group_chat_id = get_config()["GROUP_CHAT_ID"]
    if group_chat_id:
        app.job_queue.run_repeating(
            muse_visit,
            interval=SLEEP_INTERVAL,
            first=SLEEP_INTERVAL,
            data={"chat_id": group_chat_id},
        )
    else:
        logger.warning("CHAT_ID is empty; chat_mode muse job is disabled")


async def nyan_listen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_user_id = context.application.bot_data.get("bot_user_id")
    if bot_user_id and update.effective_user.id == bot_user_id:
        return
    nyan.registerMessage(update, context)


async def muse_visit(context: ContextTypes.DEFAULT_TYPE):
    # We want nyan to be visited by muse at random times, but
    # about POEMS_PER_DAY times per day.
    secondsInDay = 24 * 60 * 60
    inspirationRate = float(POEMS_PER_DAY) / float(secondsInDay / SLEEP_INTERVAL)
    if random.random() > inspirationRate:
        logger.info("checked for inspiration but it did not come")
        return

    try:
        message = nyan.write_a_poem()
        if message != "":
            job_data = context.job.data
            if not isinstance(job_data, dict):
                logger.warning("muse job data missing or invalid; skipping")
                return
            chat_id = job_data.get("chat_id")
            if not chat_id:
                logger.warning("muse job data missing chat_id; skipping")
                return
            await context.bot.send_message(chat_id=chat_id, text=message)
            # Forget messages we already wrote about.
            nyan.forget()
    except Exception as e:  # pylint: disable=broad-except
        logger.error("inspiration failed: %s", e)


def summarize(log):
    if not OPENAI_ENABLED:
        logger.info("openai disabled; skipping summary")
        return log[:200]
    prompt_user = f"Пожалуйста, сформулируй в одном преложении самую интересную тему поднятую в чате:\n{log}"
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Ты чат бот владивостокского коммьюнити разработчиков VLDC. Ты написан на python но в тайне хотел бы переписать себя на rust. Тебя зовут Нян и твой аватар это пиксельный оранжевый кот с тигриными полосками.",
                },
                {
                    "role": "user",
                    "content": prompt_user,
                },
            ],
            temperature=0.5,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
        )
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("openai summary failed: %s", exc)
        return log[:200]

    return response.choices[0].message.content
