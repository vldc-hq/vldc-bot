import collections
import functools
import time
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def timed_lru_cache(
    maxsize: int = 128, ttl: int = 60
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    A decorator to wrap a function with a lru cache that expires after ttl seconds.
    :param maxsize: The maximum size of the cache.
    :param ttl: The time to live of the cache.
    :return: The wrapped function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        cache: collections.OrderedDict[tuple[Any, ...], tuple[Any, float]] = (
            collections.OrderedDict()
        )

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            key = args + tuple(sorted(kwargs.items()))
            now = time.time()
            try:
                value, last_updated = cache[key]
                if now - last_updated > ttl:
                    del cache[key]
                else:
                    return value
            except KeyError:
                pass
            value = func(*args, **kwargs)
            cache[key] = (value, now)
            if len(cache) > maxsize:
                cache.popitem(last=False)
            return value

        return wrapper

    return decorator
