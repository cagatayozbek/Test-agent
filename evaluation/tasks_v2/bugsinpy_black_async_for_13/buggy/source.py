"""Simplified reproduction of BugsInPy black bug 13.

Bug: tokenizer stashes "async" but only flushes it when followed by "def".
For constructs like "async for", the async token is lost, leading to incorrect
parsing of async comprehensions.
"""

from typing import Iterable, Tuple, List

Token = Tuple[str, str]


def tokenize_async(tokens: Iterable[str]) -> tuple[bool, List[Token]]:
    results: List[Token] = []
    stashed = None
    async_def = False

    for tok in tokens:
        if tok == "async":
            stashed = tok
            continue

        if tok == "def" and stashed == "async":
            async_def = True
            results.append(("ASYNC", "async"))
            stashed = None

        if stashed:
            results.append(("NAME", stashed))
            stashed = None

        results.append(("NAME", tok))

    return async_def, results
