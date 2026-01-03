"""Simplified reproduction of BugsInPy PySnooper bug 1.

Bug: tracer writes unicode output without specifying UTF-8 encoding and assumes
ASCII when decoding bytes, corrupting non-ASCII characters.
"""

import io
import re
from typing import Iterable


CODING_RE = re.compile(br"coding[:=]\s*([-\w.]+)")


def detect_encoding(source: Iterable[bytes]) -> str:
    # BUG: defaults to ascii even when utf-8 is present.
    encoding = "ascii"
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
        # BUG: no encoding specified; relies on platform default
        with open(self.path, mode) as fh:
            fh.write(text)
        self.overwrite = False

    def dump_source(self, source: list[bytes]) -> str:
        encoding = detect_encoding(source)
        # BUG: uses detected encoding but assumes ascii bytes fallback
        decoded = [line.decode(encoding, "replace") for line in source]
        buffer = io.StringIO()
        for line in decoded:
            buffer.write(line)
        rendered = buffer.getvalue()
        self.write(rendered)
        return rendered
