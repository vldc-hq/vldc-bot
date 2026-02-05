import logging
import os
import random
import re
from datetime import datetime, timedelta
from random import randint
from tempfile import gettempdir
from threading import Lock
from typing import Any, Optional, TypedDict, Mapping, IO
from uuid import uuid4

import openai
import pymongo
from config import get_group_chat_id
from tg_filters import group_chat_filter
from db.mongo import get_db
from mode import cleanup_queue_update
from PIL import Image, ImageDraw, ImageFont
from pymongo.collection import Collection
from skills.mute import mute_user_for_time
from telegram import Message, Update, User
from telegram.ext import (
    MessageHandler,
    ContextTypes,
    CommandHandler,
    filters,
)
from permissions import is_admin
from typing_utils import App, get_job_queue

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
OPENAI_ENABLED = bool(OPENAI_API_KEY)

try:
    from google import genai
except Exception as exc:  # pylint: disable=broad-except
    genai = None
    logger.warning("google genai unavailable; gemini disabled: %s", exc)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai_client: Any | None = None
if genai is not None and GEMINI_API_KEY:
    try:
        genai_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("failed to init GenAI client: %s", exc)


MEME_REGEX = re.compile(r"\/[вb][иu][kк][tт][оo][pр][иu][hн][aа]", re.IGNORECASE)
GAME_TIME_SEC = 30


class PlayerRecord(TypedDict):
    _id: int
    meta: dict[str, Any]
    game_counter: int
    win_counter: int
    total_score: int
    created_at: datetime
    updated_at: datetime


class DB:
    """
    BuKToPuHa document:
    {
        _id: 420,                                   # int       -- tg user id
        meta: {...},                                # Dict      -- full tg user object (just in case)
        game_counter: 10,                           # int       -- number of games started
        win_counter: 8,                             # int       -- number of games won
        total_score: 100,                           # int       -- total score gained
        created_at: datetime(...),                  # DateTime  -- user record creation time
        updated_at: datetime(...)                  # DateTime  -- last record update time
    }
    """

    def __init__(self, db_name: str):
        self._coll: Collection[PlayerRecord] = get_db(db_name).players

    def find_all(self) -> list["PlayerRecord"]:
        return list(self._coll.find({}).sort("win_counter", pymongo.DESCENDING))

    def find(self, user_id: int) -> "PlayerRecord | None":
        return self._coll.find_one({"_id": user_id})

    def add(self, user: User, score: int = 0):
        now: datetime = datetime.now()
        game_inc = 1
        win_inc = 0
        if score > 0:
            game_inc = 0
            win_inc = 1
        return self._coll.insert_one(
            {
                "_id": user.id,
                "meta": user.to_dict(),
                "game_counter": game_inc,
                "win_counter": win_inc,
                "total_score": score,
                "created_at": now,
                "updated_at": now,
            }
        )

    def game(self, user_id: int):
        self._coll.update_one(
            {"_id": user_id},
            {
                "$inc": {
                    "game_counter": 1,
                },
                "$set": {"updated_at": datetime.now()},
            },
        )

    def win(self, user_id: int, score: int):
        self._coll.update_one(
            {"_id": user_id},
            {
                "$inc": {"win_counter": 1, "total_score": score},
                "$set": {"updated_at": datetime.now()},
            },
        )

    def remove(self, user_id: int):
        self._coll.delete_one({"_id": user_id})

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name="buktopuha")


class Buktopuha:
    def __init__(self):
        self.the_lock = Lock()
        self.word = ""
        self.started_at = None
        self.last_game_at = None
        if not OPENAI_ENABLED:
            logger.warning("OpenAI is disabled: OPENAI_API_KEY is not set")

    def get_word(self) -> str:
        with self.the_lock:
            return self.word

    def since_last_game(self) -> timedelta:
        if self.last_game_at is None:
            return timedelta(days=1)
        return datetime.now() - self.last_game_at

    def can_start(self) -> bool:
        # TODO: leaky bucket
        with self.the_lock:
            return self.since_last_game() > timedelta(minutes=1)

    def start(self, word: str):
        with self.the_lock:
            self.word = word
            self.started_at = datetime.now()
            self.last_game_at = self.started_at

    def stop(self):
        with self.the_lock:
            self.word = ""
            self.started_at = None

    def hint1(self, chat_id: int, orig_word: str):
        async def _f(context: ContextTypes.DEFAULT_TYPE):
            word = self.get_word()
            # Need to double check the word is the same
            # because game can be already stopped
            # when hint job is executed.
            if word != orig_word:
                return
            char = word[randint(0, len(word) - 1)]
            masked = re.sub(f"[^{char}]", "*", word)
            result = await context.bot.send_message(
                chat_id,
                f"First hint: {masked}",
            )
            cleanup_queue_update(
                get_job_queue(context),
                None,
                result,
                seconds=30,
            )

        return _f

    def hint2(self, chat_id: int, orig_word: str):
        async def _f(context: ContextTypes.DEFAULT_TYPE):
            word = self.get_word()
            if word != orig_word:
                return
            letters = list(word)
            random.shuffle(letters)
            anagram = "".join(letters)
            result = await context.bot.send_message(
                chat_id,
                f"Second hint (anagram): {anagram}",
            )
            cleanup_queue_update(
                get_job_queue(context),
                None,
                result,
                seconds=30,
            )

        return _f

    def end(self, chat_id: int, orig_word: str):
        async def _f(context: ContextTypes.DEFAULT_TYPE):
            word = self.get_word()
            if word != orig_word:
                return
            self.stop()
            result = await context.bot.send_message(
                chat_id,
                f"Nobody guessed the word {word} 😢",
            )
            cleanup_queue_update(
                get_job_queue(context),
                None,
                result,
                seconds=30,
            )

        return _f

    def check_for_answer(self, text: str) -> bool:
        word = self.get_word()
        return word != "" and text.lower().find(word) >= 0


def add_buktopuha(app: App, handlers_group: int):
    global wordlist
    try:
        with open("/app/words.txt", "rt", encoding="utf8") as fi:
            wordlist = fi.read().splitlines()
    except:  # noqa: E722
        logger.error("failed to read wordlist!")

    logger.info("registering buktopuha handlers")
    group_filter = group_chat_filter()

    app.add_handler(
        CommandHandler(
            "znatoki",
            show_nerds,
            block=False,
        ),
        group=handlers_group,
    )
    app.add_handler(
        # limit to groups to avoid API abuse
        MessageHandler(
            group_filter & filters.Regex(MEME_REGEX),
            start_buktopuha,
            block=False,
        ),
        group=handlers_group,
    )
    app.add_handler(
        MessageHandler(
            group_filter & filters.TEXT & ~filters.StatusUpdate.ALL,
            check_for_answer,
            block=False,
        ),
        group=handlers_group,
    )


wordlist: list[str] = [
    "babirusa",
    "gerenuk",
    "pangolin",
    "capybara",
    "platypus",
    "armadillo",
    "axolotl",
    "wombat",
]

game = Buktopuha()


def stop_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE, names: list[str]):
    job_queue = get_job_queue(context)
    if job_queue is None:
        return
    for name in names:
        for job in job_queue.get_jobs_by_name(name):
            job.schedule_removal()


async def check_for_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is None:
        return
    if update.effective_chat is None or update.message is None:
        return
    text = update.effective_message.text or ""
    if not text:
        return

    if game.check_for_answer(text):
        user = update.effective_user
        if user is None:
            return
        word = game.get_word()
        yes = random.choice(
            [
                "yes",
                "correct",
                "indeed",
                "yup",
                "yep",
                "yeah",
                "aha",
                "definetly",
                "affirmative",
                "right",
                "✅",
                "👍",
                "👏",
            ]
        )
        result = await context.bot.send_message(
            update.effective_chat.id,
            yes,
            reply_to_message_id=update.message.message_id,
        )
        game.stop()
        stop_jobs(update, context, [f"{j}-{word}" for j in ["hint1", "hint2", "end"]])

        # Felix Felicis
        if random.random() < 0.1:
            minutes = random.randint(1, 10)
            result = await context.bot.send_message(
                update.effective_chat.id,
                f"Oh, you're lucky! You get a prize: ban for {minutes} min!",
                reply_to_message_id=update.message.message_id,
            )
            await mute_user_for_time(update, context, user, timedelta(minutes=minutes))
            cleanup_queue_update(
                get_job_queue(context),
                update.message,
                result,
                30,
            )

        # game.since_last_game() at this point is the start time of the current game.
        # So the maximum score achievable is 30 + len(word) if the user guesses in zero seconds.
        score = GAME_TIME_SEC - game.since_last_game().seconds + len(word)
        existing_user = _db.find(user_id=user.id)
        if existing_user is None:
            _db.add(user=user, score=score)
        else:
            _db.win(user_id=user.id, score=score)


def generate_question(prompt: str, word: str) -> str:
    gpt_models = (
        [
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4.1",
        ]
        if OPENAI_ENABLED
        else []
    )
    gemini_models = [
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.5-pro-preview-03-25",
    ]
    models = gpt_models + (gemini_models if genai_client is not None else [])
    if not models:
        return f"Guess the word. It has {len(word)} letters."
    model = random.choice(models)
    if model.startswith("gpt"):
        try:
            response = openai.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.9,
                max_tokens=150,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0.6,
            )
            rs = response.choices[0].message.content or ""
            return f"{model}: " + re.sub(
                word, "***", rs, flags=re.IGNORECASE
            ).strip().strip('"')
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("openai question failed: %s", exc)
            return f"Guess the word. It has {len(word)} letters."
    if model.startswith("gemini") and genai_client is not None:
        try:
            resp = genai_client.models.generate_content(
                model=model,
                contents=prompt,
            )
            resp_text = resp.text or ""
            return f"{model}: " + re.sub(
                word, "***", resp_text, flags=re.IGNORECASE
            ).strip().strip('"')
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("genai question failed: %s", exc)
            return f"Guess the word. It has {len(word)} letters."

    raise Exception(f"unknown model '{model}'")


async def start_buktopuha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return
    if update.effective_chat is None:
        return
    user = update.effective_user
    if user is None:
        return

    result: Optional[Message] = None

    if not game.can_start():
        result = await context.bot.send_message(
            update.effective_chat.id,
            "Hey, not so fast!",
        )
        cleanup_queue_update(
            get_job_queue(context),
            update.message,
            result,
            10,
        )
        await mute_user_for_time(update, context, user, timedelta(minutes=1))
        return

    word = random.choice(wordlist)
    prompt = f"""You are a facilitator of an online quiz game.
    Your task is to make engaging and tricky quiz questions.
    You should try to make your question fun and interesting, but keep your wording simple and short (less than 15 words).
    Keep in mind that for part of the audience English is not a native language.
    You can use historical references or examples to explain the word.
    For expample good quiz question for word "horse" can be:
    Wooden statue of this animal helped to end the siege of Troy.

    Please write a quiz question for the word '{word}' using single sentence without mentioning the word itself."""
    try:
        question = generate_question(prompt, word)
    except:  # pylint: disable=bare-except # noqa: E722
        logger.error("Error calling GenAI model", exc_info=True)
        result = await context.bot.send_message(
            update.effective_chat.id,
            "Sorry, my GenAI brain is dizzy 😵‍💫 Try in a minute!",
        )
        cleanup_queue_update(
            get_job_queue(context),
            update.message,
            result,
            10,
        )
        game.start("")  # set last_game time, to dissallow immediate reattempts
        return

    msg = question
    if game.since_last_game() > timedelta(minutes=120):
        msg = f"🎠 Starting the BukToPuHa! 🎪\nTry to guess the word in 30seconds:\n\n{question}"

    result = await context.bot.send_message(
        update.effective_chat.id,
        msg,
    )
    game.start(word)
    job_queue = get_job_queue(context)
    if job_queue is None:
        logger.warning("job_queue missing; skipping hints")
    else:
        job_queue.run_once(
            game.hint1(update.effective_chat.id, word),
            10,
            name=f"hint1-{word}",
        )
        job_queue.run_once(
            game.hint2(update.effective_chat.id, word),
            20,
            name=f"hint2-{word}",
        )
        job_queue.run_once(
            game.end(update.effective_chat.id, word),
            30,
            name=f"end-{word}",
        )

    existing_user = _db.find(user_id=user.id)
    if existing_user is None:
        _db.add(user=user, score=0)
    else:
        _db.game(user_id=user.id)


def _is_group_chat(update: Update) -> bool:
    chat = update.effective_chat
    if chat is None:
        return False
    chat_id_or_name = get_group_chat_id()
    if not chat_id_or_name:
        return False
    try:
        return chat.id == int(chat_id_or_name)
    except ValueError:
        return chat.username == chat_id_or_name.strip("@")


async def show_nerds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leader board, I believe it should looks like smth like:

                    3HaToKu BuKToPuHbI
    ==================================================
        score   |  games  |   wins  |     znatok
    ------------+---------+---------+-----------------
    100500      | 666     | 666     | egregors
    9000        | 420     | 999     | getjump
    --------------------------------------------------

    """

    if _is_group_chat(update) and not await is_admin(update, context):
        return

    if update.effective_chat is None:
        return

    logger.error(update)
    # CSS is awesome!
    # todo:
    #  need to find out how to show board for mobile telegram as well
    board = (
        f"{'3HaToKu BuKToPuHbI'.center(52)}\n"
        f"{'=' * 55}\n"
        f"{'score'.center(12)} "
        f"| {'games'.center(9)} "
        f"| {'wins'.center(9)} "
        f"| {'znatok'.center(16)} "
        f"\n"
        f"{'-' * 12} + {'-' * 9} + {'-' * 9} + {'-' * 16}\n"
    )

    znatoki = _db.find_all()
    znatoki_length = len(znatoki)

    for znatok in znatoki:
        username = _get_username(znatok)
        board += (
            f"{str(znatok['total_score']).ljust(12)} "
            f"| {str(znatok['game_counter']).ljust(9)} "
            f"| {str(znatok['win_counter']).ljust(9)} "
            f"| {username.ljust(16)}\n"
        )

    board += f"{'-' * 55}"
    try:
        board_image, board_image_path = from_text_to_image(board, znatoki_length)
    except (ValueError, RuntimeError, OSError) as ex:
        logger.error("Cannot get image from text, znatoki error: %s", ex)
        return

    result: Optional[Message] = None

    if znatoki_length <= ZNATOKI_LIMIT_FOR_IMAGE:
        result = await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=board_image,
            disable_notification=True,
        )
    else:
        result = await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=board_image,
            disable_notification=True,
        )

    cleanup_queue_update(
        get_job_queue(context),
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )

    os.remove(board_image_path)


def _get_username(h: Mapping[str, Any]) -> str:
    """Get username or fullname or unknown"""
    m = h["meta"]
    username = m.get("username")
    fname = m.get("first_name")
    lname = m.get("last_name")
    username = username if isinstance(username, str) else None
    fname = fname if isinstance(fname, str) else None
    lname = lname if isinstance(lname, str) else None
    fullname_parts = [part for part in (fname, lname) if part]
    return username or " ".join(fullname_parts) or "unknown"


JPEG = "JPEG"
EXTENSION = ".jpg"
COLOR = "white"
MODE = "L"
FONT_SIZE = 12
ZNATOKI_LIMIT_FOR_IMAGE = 25
FONT = "firacode.ttf"


def _create_empty_image(image_path: str, limit: int) -> Image.Image | None:
    width = 480
    line_multi = 1
    header_height = 30
    line_px = FONT_SIZE * line_multi
    height = int((limit * line_px * 1.5) + header_height)
    size = (width, height)
    logger.info("Creating image")
    image = Image.new(MODE, size, COLOR)
    logger.info("Saving image")
    try:
        image.save(image_path, JPEG)
        logger.info("Empty image saved")
    except (ValueError, OSError) as ex:
        logger.error("Error during image saving, error: %s", ex)
        return None
    return image


def _add_text_to_image(text: str, image_path: str) -> Image.Image | None:
    logger.info("Adding text to image")
    image = Image.open(image_path)
    logger.info("Getting font")
    font_path = os.path.join("fonts", FONT)
    font = ImageFont.truetype(font_path, FONT_SIZE)
    logger.info("Font %s has been found", FONT)
    draw = ImageDraw.Draw(image)
    position = (45, 0)
    draw.text(xy=position, text=text, font=font)
    try:
        image.save(image_path, JPEG)
        logger.info("Image with text saved")
    except (ValueError, OSError) as ex:
        logger.error("Error during image with text saving, error: %s", ex)
        os.remove(image_path)
        return None
    return image


def from_text_to_image(text: str, limit: int) -> tuple[IO[bytes], str]:
    limit = max(limit, ZNATOKI_LIMIT_FOR_IMAGE)
    logger.info("Getting temp dir")
    tmp_dir = gettempdir()
    file_name = str(uuid4())
    image_path = f"{tmp_dir}/{file_name}{EXTENSION}"
    _create_empty_image(image_path, limit)
    _add_text_to_image(text, image_path)
    # pylint: disable=consider-using-with
    image = open(image_path, "rb")
    return image, image_path
