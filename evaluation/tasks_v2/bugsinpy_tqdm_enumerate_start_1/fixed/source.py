"""Fixed version of BugsInPy tqdm bug 1.

Fix: pass the start value to enumerate, not to tqdm_class.
"""

from typing import Iterable, Callable, Any


def _noop_tqdm(iterable: Iterable[Any], *args, **kwargs):
    return list(iterable)


def tenumerate(iterable: Iterable[Any], start: int = 0, tqdm_class: Callable = _noop_tqdm, **tqdm_kwargs):
    wrapped = tqdm_class(iterable, **tqdm_kwargs)
    return enumerate(wrapped, start)
