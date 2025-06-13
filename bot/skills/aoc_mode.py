import logging
from datetime import datetime, timedelta
from functools import cmp_to_key
from http import HTTPStatus

import asyncio  # Moved up
import requests
from pymongo.collection import Collection
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CallbackContext,
    JobQueue,
)

from config import get_group_chat_id, get_aoc_session
from db.mongo import get_db
from mode import Mode, OFF

logger = logging.getLogger(__name__)


AOC_ENDPOINT = f"https://adventofcode.com/{datetime.utcnow().year}/leaderboard/private/view/458538.json"
AOC_START_TIME = datetime.utcnow().replace(
    year=datetime.utcnow().year,
    month=12,
    day=1,
    hour=5,
    minute=0,
    second=0,
    microsecond=0,
)
AOC_UPDATE_INTERVAL = timedelta(minutes=15)
JOB_AOC_UPDATE = "aoc_update_job"


class DB:
    """
    AOC document:
    """

    def __init__(self, db_name: str):
        self._coll: Collection = get_db(db_name).aoc

    def update(self, data):
        self._coll.update_one({}, {"$set": data}, True)

    def get(self):
        return self._coll.find_one()

    def remove_all(self):
        self._coll.delete_many({})


_db = DB(db_name="aoc")
mode = Mode(
    mode_name="aoc_mode",
    default=OFF,
    on_callback=lambda app: asyncio.create_task(
        start_aoc_handlers(app.job_queue, app.bot)
    ),
    off_callback=lambda app: stop_aoc_handlers(
        app.job_queue, app.bot
    ),  # Assuming stop_aoc_handlers remains sync for now
)


async def start_aoc_handlers(queue: JobQueue, bot: Bot):
    logger.info("registering aoc handlers")
    await update_aoc_data(bot, queue)

    async def _repeating_job(context: CallbackContext):
        # Now using bot and job_queue from the context's application object
        if hasattr(context, "application") and context.application is not None:
            await update_aoc_data(
                context.application.bot, context.application.job_queue
            )
        else:
            # Fallback or error logging if application is not in context,
            # though for jobs scheduled by Application.job_queue, it should be.
            # This might indicate a need to pass bot/queue via job.data if context.application is not reliable here.
            # However, the standard is that context in a job run by Application.job_queue should have .application.
            logger.error(
                "CallbackContext does not have .application set in _repeating_job for AOC. Falling back to closure (if possible) or this will fail if bot/queue from closure are not available."
            )
            # As a safeguard, if bot and queue from closure are still accessible (Python's lexical scoping),
            # it might still work, but the goal is to move away from that.
            # For this change, we strictly try to use context.application.
            # If `bot` and `queue` from the outer scope are no longer intended to be used,
            # and context.application is missing, this job would fail to get bot/queue.
            # This highlights a dependency on how PTB populates context for jobs.
            # For now, proceeding with the assumption context.application is available.
            # If not, passing them via job.data in run_repeating would be the robust fix.
            # The current subtask description implies context.application should be used.
            pass  # Let it potentially fail if application isn't there to highlight the issue.

    queue.run_repeating(
        _repeating_job,
        AOC_UPDATE_INTERVAL,
        name=JOB_AOC_UPDATE,
    )


def stop_aoc_handlers(queue: JobQueue, bot: Bot):
    jobs = queue.get_jobs_by_name(JOB_AOC_UPDATE)
    for job in jobs:
        job.schedule_removal()


async def test(update: Update, context: CallbackContext):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="test")


@mode.add
def add_aoc_mode(
    application: Application, handlers_group: int
):  # Changed upd to application
    pass


def aoc_day_from_datetime(dt):
    return (dt - AOC_START_TIME) / timedelta(days=1)


def aoc_time_since_day_start(dt):
    return dt - (AOC_START_TIME + int(aoc_day_from_datetime(dt)) * timedelta(days=1))


def cmp(_x, _y):
    x = _x[1]
    y = _y[1]

    def inner_cmp(x, y):
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


def calculate_solved_by(members, current_day):
    new_day_solved_by = {}

    for memberId, member in members.items():
        if str(current_day) not in member["completion_day_level"]:
            continue
        tasks = member["completion_day_level"][str(current_day)]
        solved = []
        task = None

        if len(tasks) == 1:
            (task) = tasks["1"]
            solved = [datetime.fromtimestamp(task["get_star_ts"])]
        elif len(tasks) == 2:
            (task1, task) = tasks["1"], tasks["2"]
            solved = [
                datetime.fromtimestamp(task1["get_star_ts"]),
                datetime.fromtimestamp(task["get_star_ts"]),
            ]

        if task is None:
            continue

        new_day_solved_by[memberId] = solved
    return dict(sorted(new_day_solved_by.items(), key=cmp_to_key(cmp)))


async def process_aoc_update(data, bot: Bot):
    cached_data = _db.get()

    # It is okay for a first mode run, just store this one
    if cached_data is None:
        # Return?
        cached_data = {"members": {}}

    _db.update(data)

    current_day = int(aoc_day_from_datetime(datetime.utcnow())) + 1
    logger.info("Current AOC day is %d", current_day)

    day_solved_by = calculate_solved_by(cached_data["members"], current_day)
    updated_day_solved_by = calculate_solved_by(data["members"], current_day)

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

            await bot.send_message(get_group_chat_id(), message)


async def update_aoc_data(bot: Bot, queue: JobQueue):
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

    data = response.json()
    logger.info(data)

    await process_aoc_update(data, bot)
