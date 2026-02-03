import logging
import os
import re
from datetime import datetime, timedelta
from random import randint
from tempfile import gettempdir
from threading import Lock
from typing import List, Optional, Tuple, Dict
from uuid import uuid4

import pymongo
from PIL import Image, ImageDraw, ImageFont
from pymongo.collection import Collection
from telegram import Update, User, Message
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import get_group_chat_id
from db.mongo import get_db
from handlers import ChatCommandHandler
from mode import cleanup_queue_update
from skills.mute import mute_user_for_time
from permissions import is_admin

logger = logging.getLogger(__name__)

MUTE_MINUTES = 16 * 60  # 16h
NUM_BULLETS = 6
HUSSARS_LIMIT_FOR_IMAGE = 25
FONT = "firacode.ttf"


class DB:
    """
    Hussar document:
    {
        _id: 420,                                   # int       -- tg user id
        meta: {...},                                # Dict      -- full tg user object (just in case)
        shot_counter: 10,                           # int       -- full amount of shots
        miss_counter: 8,                            # int       -- amount of miss
        dead_counter: 2,                            # int       -- amount of dead shots
        total_time_in_club: datetime(...),          # DateTime  -- all time in the club
        first_shot": datetime(...),                 # DateTIme  -- time of first shot
        "last_shot": datetime(...)                  # DateTIme  -- time of last shot
    }
    """

    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).hussars

    def find_all(self):
        return list(self._coll.find({}).sort("total_time_in_club", pymongo.DESCENDING))

    def find(self, user_id: str):
        return self._coll.find_one({"_id": user_id})

    def add(self, user: User):
        now: datetime = datetime.now()
        return self._coll.insert_one(
            {
                "_id": user.id,
                "meta": user.to_dict(),
                "shot_counter": 0,
                "miss_counter": 0,
                "dead_counter": 0,
                "total_time_in_club": timedelta().seconds,
                # TODO: wat about ranks?
                # "rank": meh,
                "first_shot": now,
                "last_shot": now,
            }
        )

    def dead(self, user_id: str, mute_min: int):
        self._coll.update_one(
            {"_id": user_id},
            {
                "$inc": {
                    "shot_counter": 1,
                    "dead_counter": 1,
                    "total_time_in_club": mute_min * 60,
                },
                "$set": {"last_shot": datetime.now()},
            },
        )

    def miss(self, user_id: str):
        self._coll.update_one(
            {"_id": user_id},
            {
                "$inc": {"shot_counter": 1, "miss_counter": 1},
                "$set": {"last_shot": datetime.now()},
            },
        )

    def remove(self, user_id: str):
        self._coll.delete_one({"_id": user_id})

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name="roll")

MEME_REGEX = re.compile(r"\/[rрp][оo0][1lл]{2}", re.IGNORECASE)


def add_roll(app: Application, handlers_group: int):
    logger.info("registering roll handlers")
    app.add_handler(MessageHandler(filters.Dice.ALL, roll), group=handlers_group)
    app.add_handler(
        MessageHandler(filters.Regex(MEME_REGEX), roll, block=False),
        group=handlers_group,
    )
    app.add_handler(
        ChatCommandHandler(
            "gdpr_me",
            satisfy_GDPR,
        ),
        group=handlers_group,
    )
    app.add_handler(
        CommandHandler(
            "hussars",
            show_hussars,
            block=False,
        ),
        group=handlers_group,
    )
    app.add_handler(
        ChatCommandHandler(
            "htop",
            show_active_hussars,
            require_admin=True,
        ),
        group=handlers_group,
    )
    app.add_handler(
        ChatCommandHandler(
            "wipe_hussars",
            wipe_hussars,
            require_admin=True,
        ),
        group=handlers_group,
    )


barrel_lock = Lock()


def _reload(context: ContextTypes.DEFAULT_TYPE) -> List[bool]:
    empty, bullet = False, True
    barrel: List[bool] = [empty] * NUM_BULLETS
    lucky_number = randint(0, NUM_BULLETS - 1)
    barrel[lucky_number] = bullet
    context.chat_data["barrel"] = barrel

    return barrel


def get_miss_string(shots_remain: int) -> str:
    s = ["😕", "😟", "😥", "😫", "😱"]
    misses = ["🔘"] * (NUM_BULLETS - shots_remain)
    chances = ["⚪️"] * shots_remain
    barrel_str = "".join(misses + chances)
    h = get_mute_minutes(shots_remain - 1) // 60
    return f"{s[NUM_BULLETS - shots_remain - 1]}🔫 MISS! Barrel: {barrel_str}, {h}h"


def get_mute_minutes(shots_remain: int) -> int:
    return MUTE_MINUTES * (NUM_BULLETS - shots_remain)


def _shot(context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, int]:
    with barrel_lock:
        barrel = context.chat_data.get("barrel")
        if barrel is None or len(barrel) == 0:
            barrel = _reload(context)

        logger.debug("barrel before shot: %s", barrel)

        fate = barrel.pop()
        context.chat_data["barrel"] = barrel
        shots_remained = len(barrel)  # number before reload
        if fate:
            _reload(context)

    return fate, shots_remained


def _get_username(h: Dict) -> str:
    """Get username or fullname or unknown"""
    m = h["meta"]
    username = m.get("username")
    fname = m.get("first_name")
    lname = m.get("last_name")
    return (
        username
        or " ".join(filter(lambda x: x is not None, [fname, lname]))
        or "unknown"
    )


JPEG = "JPEG"
EXTENSION = ".jpg"
COLOR = "white"
MODE = "L"
FONT_SIZE = 12


def _create_empty_image(image_path, limit):
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


def _add_text_to_image(text, image_path):
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


def from_text_to_image(text, limit):
    limit = max(limit, HUSSARS_LIMIT_FOR_IMAGE)
    logger.info("Getting temp dir")
    tmp_dir = gettempdir()
    file_name = str(uuid4())
    image_path = f"{tmp_dir}/{file_name}{EXTENSION}"
    _create_empty_image(image_path, limit)
    _add_text_to_image(text, image_path)
    # pylint: disable=consider-using-with
    image = open(image_path, "rb")
    return image, image_path


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


async def show_hussars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leader board, I believe it should looks like smth like:

                           Hussars leader board
    ====================================================
       time in club    | attempts | deaths |      hussar
    ------------------ + -------- + ------ + -----------
    2 days, 15:59:54   | 6        | 6      | egregors
    15:59:59           | 1        | 1      | getjump
    ----------------------------------------------------

    """
    if _is_group_chat(update) and not await is_admin(update, context):
        return
    # CSS is awesome!
    # todo:
    #  need to find out how to show board for mobile telegram as well
    board = (
        f"{'Hussars leader board'.center(52)}\n"
        f"{''.rjust(51, '=')}\n"
        f"{'time in club'.center(18)} "
        f"| {'attempts'.center(8)} "
        f"| {'deaths'.center(6)} "
        f"| {'hussar'.center(11)} "
        f"\n"
        f"{''.ljust(18, '-')} + {''.ljust(8, '-')} + {''.ljust(6, '-')} + {''.ljust(11, '-')}\n"
    )

    hussars = _db.find_all()
    hussars_length = len(hussars)

    for hussar in hussars:
        username = _get_username(hussar)
        board += (
            f"{str(timedelta(seconds=hussar['total_time_in_club'])).ljust(18)} "
            f"| {str(hussar['shot_counter']).ljust(8)} "
            f"| {str(hussar['dead_counter']).ljust(6)} "
            f"| {username.ljust(15)}\n"
        )

    board += f"{''.rjust(51, '-')}"
    try:
        board_image, board_image_path = from_text_to_image(board, hussars_length)
    except (ValueError, RuntimeError, OSError) as ex:
        logger.error("Cannot get image from text, hussars error: %s", ex)
        return

    result: Optional[Message] = None

    if hussars_length <= HUSSARS_LIMIT_FOR_IMAGE:
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
        context.job_queue,
        update.message,
        result,
        600,
        remove_cmd=True,
        remove_reply=False,
    )

    os.remove(board_image_path)


async def show_active_hussars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hussars = _db.find_all()

    message = "No hussars in da club 😒"

    restricted_hussars = []

    for hussar in hussars:
        try:
            chat_member = await context.bot.get_chat_member(
                update.effective_chat.id, hussar.get("_id")
            )

            if chat_member.status == ChatMemberStatus.RESTRICTED:
                restricted_hussars.append(hussar)

        except BadRequest:
            logger.warning("can't get user %s, skip", hussar)

    if len(restricted_hussars) > 0:
        message = "Right meow in da club ☠️:\n"

        for hussar in restricted_hussars:
            name = _get_username(hussar)
            magia_nombro = sum([ord(c) for c in name])
            emoji = chr(ord("😀") + magia_nombro % 75)
            message += f"{emoji} {name} \n"

    result = await context.bot.send_message(update.effective_chat.id, message)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
    )


async def roll(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user: User = update.effective_user
    result: Optional[Message] = None
    # check if hussar already exist or create new one
    existing_user = _db.find(user_id=user.id)
    if existing_user is None:
        _db.add(user=user)

    is_shot, shots_remained = _shot(context)
    shot_result = "he is dead!" if is_shot else "miss!"
    logger.info(
        "user: %s[%s] is rolling and... %s", user.full_name, user.id, shot_result
    )

    if is_shot:
        # todo: https://github.com/vldc-hq/vldc-bot/issues/93
        #  if bot can't restrict user, user should be passed into towel-mode like state

        mute_min = get_mute_minutes(shots_remained)
        result = await context.bot.send_message(
            update.effective_chat.id,
            f"💥 boom! {user.full_name} 😵 [{mute_min // 60}h mute]",
        )

        await mute_user_for_time(update, context, user, timedelta(minutes=mute_min))
        _db.dead(user.id, mute_min)
    else:

        # lucky one
        _db.miss(user.id)

        result = await context.bot.send_message(
            update.effective_chat.id,
            f"{user.full_name}: {get_miss_string(shots_remained)}",
        )

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


# noinspection PyPep8Naming
async def satisfy_GDPR(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user: User = update.effective_user

    _db.remove(user.id)
    logger.info("%s was removed from DB", user.full_name)
    result = await update.message.reply_text("ok, boomer 😒", disable_notification=True)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )


async def wipe_hussars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _db.remove_all()
    logger.info("all hussars was removed from DB")
    result = await update.message.reply_text("👍", disable_notification=True)

    cleanup_queue_update(
        context.job_queue,
        update.message,
        result,
        120,
        remove_cmd=True,
        remove_reply=False,
    )
