"""Fixed version of BugsInPy PySnooper bug 1.

Fixes:
- Default to UTF-8 for byte decoding.
- Always write files with explicit UTF-8 encoding.
"""

import io
import re
from typing import Iterable


CODING_RE = re.compile(br"coding[:=]\s*([-\w.]+)")


def detect_encoding(source: Iterable[bytes]) -> str:
    encoding = "utf-8"
    for line in source:
        match = CODING_RE.search(line)
        if match:
            encoding = match.group(1).decode("ascii", "ignore")
            break
    return encoding


class Tracer:
    def __init__(self, path: str, overwrite: bool = False):
        self.path = path
        self.overwrite = overwrite

    def write(self, text: str) -> None:
        mode = "w" if self.overwrite else "a"
        with open(self.path, mode, encoding="utf-8") as fh:
            fh.write(text)
        self.overwrite = False

    def dump_source(self, source: list[bytes]) -> str:
        encoding = detect_encoding(source)
        decoded = [line.decode(encoding, "replace") for line in source]
        buffer = io.StringIO()
        for line in decoded:
            buffer.write(line)
        rendered = buffer.getvalue()
        self.write(rendered)
        return rendered
