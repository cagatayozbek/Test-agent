"""Simplified reproduction of BugsInPy thefuck bug 28.

Bug: fix_file rule ignores column-aware settings and fails to escape
parentheses in patterns, so certain stack traces are not matched and the
editor command is built without column support.
"""

import os
import re
from typing import Mapping

# BUG: Parentheses are not escaped and ordering hides the more specific
# pattern with columns. This causes matches like "file.py (line 3):" to fail
# and column info to be ignored.
PATTERNS = (
    r"^(?P<file>[^:]+) \(line (?P<line>\d+)\):",
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+)",
    r"^(?P<file>[^:]+): line (?P<line>\d+):",
)

DEFAULT_SETTINGS: Mapping[str, str | None] = {
    "fixlinecmd": "{editor} {file} +{line}",
    "fixcolcmd": None,
}


def _search(text: str) -> re.Match | None:
    """Return the first regex match for a stack trace line."""
    for pat in PATTERNS:
        match = re.search(pat, text, re.MULTILINE)
        if match:
            return match
    return None


def get_new_command(stderr: str, settings: Mapping[str, str | None] | None = None) -> str | None:
    """Build an editor command for the first matched stack trace.

    BUG: Ignores column-aware formatting and relies on the flawed patterns
    above, so some traces are missed and the cursor is not placed precisely.
    """
    settings = settings or DEFAULT_SETTINGS
    match = _search(stderr)
    if not match:
        return None

    editor = os.environ.get("EDITOR", "vim")
    return settings["fixlinecmd"].format(
        editor=editor,
        file=match.group("file"),
        line=match.group("line"),
    )
