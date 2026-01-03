"""Fixed version of BugsInPy thefuck bug 3.

Fix: use a non-interactive version command and extract only the version token.
"""

from typing import Callable, Iterable


def _default_runner(cmd: Iterable[str]) -> str:
    return "fish, version 3.1.2\n"


def fish_info(run_command: Callable[[Iterable[str]], str] = _default_runner) -> str:
    output = run_command(["fish", "--version"])
    parts = output.strip().split()
    version = parts[-1] if parts else ""
    return f"Fish Shell {version}"
