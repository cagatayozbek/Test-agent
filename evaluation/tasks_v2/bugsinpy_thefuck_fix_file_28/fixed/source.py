"""Fixed version of BugsInPy thefuck bug 28 (fix_file rule).

Fixes:
- Escape parentheses and reorder patterns so column-aware matches are not lost.
- Apply wrap_settings-style defaults and honor column-aware command formatting.
"""

import os
import re
from typing import Callable, Mapping

PATTERNS = (
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+)",
    r"^(?P<file>[^:]+): line (?P<line>\d+):",
    r"^(?P<file>[^:]+) \(line (?P<line>\d+)\):",
)

DEFAULT_SETTINGS: Mapping[str, str | None] = {
    "fixlinecmd": "{editor} {file} +{line}",
    "fixcolcmd": None,
}


def wrap_settings(defaults: Mapping[str, str | None]) -> Callable:
    """Decorator to merge caller settings with defaults."""

    def decorator(fn: Callable) -> Callable:
        def wrapper(stderr: str, settings: Mapping[str, str | None] | None = None):
            merged = dict(defaults)
            if settings:
                merged.update(settings)
            return fn(stderr, merged)

        return wrapper

    return decorator


def _search(text: str) -> re.Match | None:
    for pat in PATTERNS:
        match = re.search(pat, text, re.MULTILINE)
        if match:
            return match
    return None


@wrap_settings(DEFAULT_SETTINGS)
def get_new_command(stderr: str, settings: Mapping[str, str | None]) -> str | None:
    match = _search(stderr)
    if not match:
        return None

    editor = os.environ.get("EDITOR", "vim")
    groups = match.groupdict()

    if settings.get("fixcolcmd") and groups.get("col"):
        return settings["fixcolcmd"].format(
            editor=editor,
            file=groups["file"],
            line=groups["line"],
            col=groups["col"],
        )

    return settings["fixlinecmd"].format(
        editor=editor,
        file=groups["file"],
        line=groups["line"],
    )
