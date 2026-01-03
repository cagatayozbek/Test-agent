"""Simplified reproduction of BugsInPy thefuck bug 3.

Bug: fish version lookup shells out with an interactive command and keeps the
full output string, leading to brittle parsing (e.g., trailing text or
newlines). Tests should notice that the reported version still contains the
prefix.
"""

from typing import Callable, Iterable


def _default_runner(cmd: Iterable[str]) -> str:
    # Deterministic placeholder output; avoids calling external fish binary.
    return "fish, version 3.1.2\n"


def fish_info(run_command: Callable[[Iterable[str]], str] = _default_runner) -> str:
    output = run_command(["fish", "-c", "echo $FISH_VERSION"])
    # BUG: keeps full output, including prefix/newline
    return f"Fish Shell {output.strip()}"
