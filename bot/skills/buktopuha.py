import logging
import os
import random
import re
from datetime import datetime, timedelta
from random import randint
from tempfile import gettempdir
from threading import Lock
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import openai
import pymongo
from config import get_group_chat_id
from db.mongo import get_db
from filters import admin_filter
from handlers import ChatCommandHandler
from mode import cleanup_queue_update
from PIL import Image, ImageDraw, ImageFont
from pymongo.collection import Collection
from skills.mute import mute_user_for_time
from telegram import ChatMember, Message, Update, User
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Updater
from telegram.ext.filters import Filters

openai.api_key = os.getenv("OPENAI_API_KEY")


logger = logging.getLogger(__name__)


MEME_REGEX = re.compile(r"\/[вb][иu][kк][tт][оo][pр][иu][hн][aа]", re.IGNORECASE)
GAME_TIME_SEC = 30


class Buktopuha:
    def __init__(self):
        self.the_lock = Lock()
        self.word = ""
        self.started_at = None
        self.last_game_at = None

    def get_word(self) -> str:
        with self.the_lock:
            return self.word

    def can_start(self) -> bool:
        # TODO: leaky bucket
        with self.the_lock:
            return (
                self.last_game is None
                or self.last_game < datetime.now() - timedelta(minutes=1)
            )

    def start(self, word: str):
        with self.the_lock:
            self.word = word
            self.started_at = datetime.now()
            self.last_game = self.started_at

    def stop(self):
        with self.the_lock:
            self.word = ""
            self.started_at = None

    def hint1(self, id):
        def _f(context: CallbackContext):
            word = self.get_word()
            char = word[randint(0, len(word) - 1)]
            masked = re.sub(f"[^{char}]", "*", word)
            context.bot.send_message(
                id,
                f"First hint: {masked}",
            )

        return _f

    def hint2(self, id):
        def _f(context: CallbackContext):
            word = list(self.get_word())
            random.shuffle(word)
            anagram = "".join(word)
            context.bot.send_message(
                id,
                f"Second hint (anagram): {anagram}",
            )

        return _f

    def end(self, id):
        def _f(context: CallbackContext):
            word = self.get_word()
            self.stop()
            context.bot.send_message(
                id,
                f"Nobody guessed the word {word} :(",
            )

        return _f

    def check_for_answer(self, text: str):
        word = self.get_word()
        return word != "" and text.lower().find(word) >= 0


def add_buktopuha(upd: Updater, handlers_group: int):
    logger.info("registering buktopuha handlers")
    dp = upd.dispatcher
    dp.add_handler(
        MessageHandler(Filters.regex(MEME_REGEX), start_buktopuha, run_async=True),
        handlers_group,
    )
    dp.add_handler(
        MessageHandler(Filters.regex(MEME_REGEX), start_buktopuha, run_async=True),
        handlers_group,
    )


WORDLIST = [
    "concrete",
    "pillar",
    "motorcycle",
    "cappucino",
    "platypus",
    "armadillo",
    "headphones",
]
game = Buktopuha()


def stop_jobs(update: Update, context: CallbackContext, names: list(str)):
    for job in context.job_queue._queue.queue:
        if job[1].name in names:
            try:
                context.job_queue._queue.queue.remove(job)
            except Exception as ex:
                logger.error("failed to remove job %s", job[1].name, exc_info=1)


def check_for_answer(update: Update, context: CallbackContext):
    if update.message is None:
        return

    user: User = update.effective_user
    result: Optional[Message] = None

    if game.check_for_answer(self, update.message.text):
        word = self.get_word()
        context.bot.send_message(
            update.effective_chat.id,
            f"Congrats {user.name}! 🎉\nThe answer was {word}!",
        )
        game.stop()
        stop_jobs(update, context, [f"{j}-{word}" for j in ["hint1", "hint2", "end"]])


def start_buktopuha(update: Update, context: CallbackContext):
    if update.message is None:
        return

    user: User = update.effective_user
    result: Optional[Message] = None

    if not game.can_start():
        result = context.bot.send_message(
            update.effective_chat.id,
            f"Hey, not so fast!",
        )
        cleanup_queue_update(
            context.job_queue,
            update.message,
            result,
            10,
        )

    word = random.choice(WORDLIST)
    prompt = f"""You are a facilitator of an online quiz game.
    Your task is to make engaging and tricky quiz questions.
    Please explain the word '{word}' with a single sentence."""
    try:
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            temperature=0.9,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0.6,
        )
        rs = response["choices"][0]["text"]
        question = re.sub(word, "***", rs, flags=re.IGNORECASE).strip()
    except Exception as ex:
        logger.error("Error calling OpenAI API", exc_info=1)
        result = context.bot.send_message(
            update.effective_chat.id,
            f"Sorry, my GPT brain is dizzy 😵‍💫 Try in a minute!",
        )
        cleanup_queue_update(
            context.job_queue,
            update.message,
            result,
            10,
        )
        game.start("")  # set last_game time, to dissallow immediate reattempts
        return

    result = context.bot.send_message(
        update.effective_chat.id,
        f"Starting the BukToPuHa!\nTry to guess the word in 30seconds.\n{question}",
    )

    game.start(word)
    context.job_queue.run_once(
        game.hint1(update.effective_chat.id), 10, context=context, name=f"hint1-{word}"
    )
    context.job_queue.run_once(
        game.hint2(update.effective_chat.id), 20, context=context, name=f"hint2-{word}"
    )
    context.job_queue.run_once(
        game.end(update.effective_chat.id), 30, context=context, name=f"end-{word}"
    )
