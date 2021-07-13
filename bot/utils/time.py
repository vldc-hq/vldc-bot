import logging
from datetime import timedelta
from functools import reduce

logger = logging.getLogger(__name__)


def get_duration(raw_duration: str) -> timedelta:
    """Convert duration string like `4w 7d 2h 20m 48s` to python timedelta"""

    _dispatcher = {
        "w": lambda total_duration, duration: total_duration
        + timedelta(weeks=duration),
        "d": lambda total_duration, duration: total_duration + timedelta(days=duration),
        "h": lambda total_duration, duration: total_duration
        + timedelta(hours=duration),
        "m": lambda total_duration, duration: total_duration
        + timedelta(minutes=duration),
        "s": lambda total_duration, duration: total_duration
        + timedelta(seconds=duration),
    }

    def f(acc: timedelta, el: str) -> timedelta:
        try:
            if not any(
                [
                    "w" in el,
                    "d" in el,
                    "h" in el,
                    "m" in el,
                    "s" in el,
                ]
            ):
                return acc + timedelta(minutes=int(el))

            mark = el[-1]
            count = int(el[:-1])

            return _dispatcher[mark](acc, count)

        except ValueError as err:
            logger.error("can't convert durations: %s", err)
            return acc

    return reduce(f, filter(lambda x: x, raw_duration.split(" ")), timedelta())
