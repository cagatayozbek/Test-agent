import pytest
import os
from source import Tracer, detect_encoding

def test_unicode_corruption():
    """Test that non-ASCII characters are not corrupted when written to file.

    Bug: Tracer defaults to ASCII and writes files without specifying UTF-8,
    corrupting non-ASCII output.
    """
    filepath = "test_output.txt"
    tracer = Tracer(filepath, overwrite=True)
    test_string = "你好世界"
    tracer.write(test_string)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    assert content == test_string, \
        f"Expected '{test_string}', but got '{content}'"


def test_detect_encoding_utf8():
    """Test that detect_encoding correctly identifies UTF-8 encoding when present.

    Bug: detect_encoding defaults to ascii even when utf-8 is present.
    """
    utf8_source = [b'# coding: utf-8', b'print("Hello")']
    encoding = detect_encoding(utf8_source)
    assert encoding == 'utf-8', f"Expected utf-8, but got {encoding}"