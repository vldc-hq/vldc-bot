import logging
from datetime import timedelta
from functools import reduce

logger = logging.getLogger(__name__)


def get_duration(raw_duration: str) -> timedelta:
    """ Convert duration string like `2h 20m 48s` to python timedelta """

    def f(acc: timedelta, el: str) -> timedelta:
        try:
            if not any(['h' in el, 'm' in el, 's' in el]):
                return acc + timedelta(minutes=int(el))

            mark = el[-1]
            count = int(el[:-1])

            if mark == 'h':
                return acc + timedelta(hours=count)
            if mark == 'm':
                return acc + timedelta(minutes=count)
            if mark == 's':
                return acc + timedelta(seconds=count)

            return acc + timedelta(minutes=int(el))

        except ValueError as err:
            logger.error("can't convert durations: %s", err)
            return acc

    return reduce(f, filter(lambda x: x, raw_duration.split(' ')), timedelta())
