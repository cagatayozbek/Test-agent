"""Simplified reproduction of BugsInPy tqdm bug 1.

Bug: tenumerate passes the start value positionally into tqdm_class, causing
the enumerate start value to be ignored and shifting counts.
"""

from typing import Iterable, Callable, Any


def _noop_tqdm(iterable: Iterable[Any], *args, **kwargs):
    # Stand-in for tqdm; returns a concrete list for determinism in tests.
    return list(iterable)


def tenumerate(iterable: Iterable[Any], start: int = 0, tqdm_class: Callable = _noop_tqdm, **tqdm_kwargs):
    # BUG: start forwarded to tqdm_class instead of enumerate
    wrapped = tqdm_class(iterable, start, **tqdm_kwargs)
    return enumerate(wrapped)
