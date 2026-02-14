import logging
from datetime import datetime, timedelta, timezone
from functools import cmp_to_key
from http import HTTPStatus
from typing import Any

import requests
from telegram import Update, Bot
from telegram.ext import ContextTypes

from config import get_group_chat_id, get_aoc_session
from db.sqlite import db
from mode import Mode, OFF
from typing_utils import App, JobQueueT

logger = logging.getLogger(__name__)


_now_utc = datetime.now(timezone.utc)
AOC_ENDPOINT = (
    f"https://adventofcode.com/{_now_utc.year}/leaderboard/private/view/458538.json"
)
AOC_START_TIME = _now_utc.replace(
    year=_now_utc.year,
    month=12,
    day=1,
    hour=5,
    minute=0,
    second=0,
    microsecond=0,
)
AOC_UPDATE_INTERVAL = timedelta(minutes=15)
JOB_AOC_UPDATE = "aoc_update_job"


mode = Mode(
    mode_name="aoc_mode",
    default=OFF,
    on_callback=lambda app: start_aoc_handlers(app.job_queue),
    off_callback=lambda app: stop_aoc_handlers(app.job_queue),
)


def start_aoc_handlers(queue: JobQueueT | None):
    logger.info("registering aoc handlers")
    if queue is None:
        return
    queue.run_repeating(
        update_aoc_data,
        AOC_UPDATE_INTERVAL,
        name=JOB_AOC_UPDATE,
    )
    queue.run_once(update_aoc_data, 0)


def stop_aoc_handlers(queue: JobQueueT | None):
    if queue is None:
        return
    jobs = queue.get_jobs_by_name(JOB_AOC_UPDATE)
    for job in jobs:
        job.schedule_removal()


async def test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat is None:
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="test")


@mode.add
def add_aoc_mode(app: App, handlers_group: int):
    pass


def aoc_day_from_datetime(dt: datetime) -> float:
    return (dt - AOC_START_TIME) / timedelta(days=1)


def aoc_time_since_day_start(dt: datetime) -> timedelta:
    return dt - (AOC_START_TIME + int(aoc_day_from_datetime(dt)) * timedelta(days=1))


def cmp(_x: tuple[Any, Any], _y: tuple[Any, Any]) -> int:
    x = _x[1]
    y = _y[1]

    def inner_cmp(x: Any, y: Any) -> int:
        if x < y:
            return -1
        if y < x:
            return 1
        return 0

    if len(x) == len(y) == 2:
        return inner_cmp(x[1], y[1])
    if len(x) >= 1 and len(y) >= 1:
        return inner_cmp(x[0], y[0])
    return 0


def calculate_solved_by(
    members: dict[str, Any], current_day: int
) -> dict[str, list[datetime]]:
    new_day_solved_by: dict[str, list[datetime]] = {}

    for memberId, member in members.items():
        if str(current_day) not in member["completion_day_level"]:
            continue
        tasks = member["completion_day_level"][str(current_day)]
        solved = []
        task = None

        if len(tasks) == 1:
            task = tasks["1"]
            solved = [datetime.fromtimestamp(task["get_star_ts"])]
        elif len(tasks) == 2:
            task1, task = tasks["1"], tasks["2"]
            solved = [
                datetime.fromtimestamp(task1["get_star_ts"]),
                datetime.fromtimestamp(task["get_star_ts"]),
            ]

        if task is None:
            continue

        new_day_solved_by[memberId] = solved
    return dict(sorted(new_day_solved_by.items(), key=cmp_to_key(cmp)))


async def process_aoc_update(data: dict[str, Any], bot: Bot) -> None:
    cached_data = db.get_aoc_data() or {"members": {}}

    # It is okay for a first mode run, just store this one
    db.update_aoc_data(data)

    current_day = int(aoc_day_from_datetime(datetime.now(timezone.utc))) + 1
    logger.info("Current AOC day is %d", current_day)

    day_solved_by = calculate_solved_by(cached_data.get("members", {}), current_day)
    updated_day_solved_by = calculate_solved_by(data.get("members", {}), current_day)

    solved_both = False
    for _, tasks in day_solved_by.items():
        if len(tasks) == 2:
            solved_both = True

    logger.info(day_solved_by)
    logger.info(updated_day_solved_by)

    if len(updated_day_solved_by) > 0 and solved_both is False:
        # someone has done both current day task
        # find out who was first from sorted array
        first_one = None

        for memberId, tasks in updated_day_solved_by.items():
            if len(tasks) == 2:
                first_one = (memberId, tasks)
                break

        logger.info(first_one)
        if first_one is not None:
            member = data["members"][first_one[0]]
            max_delta = max(
                aoc_time_since_day_start(first_one[1][0]),
                aoc_time_since_day_start(first_one[1][1]),
            )

            message = (
                f"Wow! @{member['name']} just solves Day {current_day}"
                f" problem in {str(max_delta)}, gaining {member['stars']} ⭐️!"
                " Gut Gemacht! 🔥🔥🔥"
            )

            group_chat_id = get_group_chat_id()
            if group_chat_id:
                await bot.send_message(group_chat_id, message)
            else:
                logger.warning("CHAT_ID is empty; skipping AOC notification")


async def update_aoc_data(context: ContextTypes.DEFAULT_TYPE) -> None:
    bot = context.bot
    aoc_session = get_aoc_session()

    if aoc_session is None:
        logging.error("AOC session was not set in environment")
        return

    response = requests.get(
        AOC_ENDPOINT, cookies={"session": aoc_session}, allow_redirects=False, timeout=3
    )

    if response.status_code != HTTPStatus.OK:
        logging.error("AOC response error %d %s", response.status_code, response.text)
        return

    data: dict[str, Any] = response.json()
    logger.info(data)

    await process_aoc_update(data, bot)
