import pytest
from source import Tracer
import os

def test_unicode_output_corruption():
    """Test that unicode output is not corrupted when written to file.\n
    Bug: Tracer.write doesn't specify encoding, causing corruption of non-ASCII characters.
    """
    test_file_path = "test_unicode_file.txt"
    tracer = Tracer(path=test_file_path, overwrite=True)
    unicode_text = "你好世界"

    tracer.write(unicode_text)

    with open(test_file_path, "r", encoding="utf-8") as f:
        read_text = f.read()

    assert read_text == unicode_text, f"Expected '{unicode_text}', but got '{read_text}'"

    os.remove(test_file_path)