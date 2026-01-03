"""Fixed version of BugsInPy black bug 13.

Fix: treat both "async def" and "async for" specially; only mark async_def
for the function case while still emitting the ASYNC token for loops.
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

        if tok in ("def", "for") and stashed == "async":
            if tok == "def":
                async_def = True
            results.append(("ASYNC", "async"))
            stashed = None

        if stashed:
            results.append(("NAME", stashed))
            stashed = None

        results.append(("NAME", tok))

    return async_def, results
