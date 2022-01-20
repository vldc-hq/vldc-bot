import logging
from datetime import datetime, timedelta
from functools import cmp_to_key

from http import HTTPStatus

import requests
from config import get_group_chat_id, get_aoc_session

from db.mongo import get_db
from mode import Mode, OFF

from pymongo.collection import Collection

from telegram import Update, Bot
from telegram.ext import (
    Updater,
    CallbackContext,
    JobQueue,
)

logger = logging.getLogger(__name__)

AOC_ENDPOINT = "https://adventofcode.com/2021/leaderboard/private/view/458538.json"
AOC_START_TIME = datetime.fromtimestamp(1638334800)
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
    on_callback=lambda dp: start_aoc_handlers(dp.job_queue, dp.bot),
    off_callback=lambda dp: stop_aoc_handlers(dp.job_queue, dp.bot),
)


def start_aoc_handlers(queue: JobQueue, bot: Bot):
    logger.info("registering aoc handlers")
    update_aoc_data(bot, queue)
    queue.run_repeating(
        lambda _: update_aoc_data(bot, queue),
        AOC_UPDATE_INTERVAL,
        name=JOB_AOC_UPDATE,
    )


def stop_aoc_handlers(queue: JobQueue, bot: Bot):
    jobs = queue.get_jobs_by_name(JOB_AOC_UPDATE)
    for job in jobs:
        job.schedule_removal()


def test(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="test")


@mode.add
def add_aoc_mode(upd: Updater, handlers_group: int):
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


def process_aoc_update(data, bot: Bot):
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

            bot.send_message(get_group_chat_id(), message)


def update_aoc_data(bot: Bot, queue: JobQueue):
    aoc_session = get_aoc_session()

    if aoc_session is None:
        logging.error("AOC session was not set in environment")
        return

    response = requests.get(
        AOC_ENDPOINT, cookies={"session": aoc_session}, allow_redirects=False
    )

    if response.status_code != HTTPStatus.OK:
        logging.error("AOC response error %d %s", response.status_code, response.text)
        return

    data = response.json()
    logger.info(data)

    process_aoc_update(data, bot)
