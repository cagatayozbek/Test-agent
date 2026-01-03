import pytest
from pathlib import Path
from source import Tracer

def test_dump_source_with_unicode_no_coding_declaration(tmp_path: Path):
    """
    Tests that dump_source correctly handles unicode source bytes that lack
    a 'coding:' declaration.

    Bug: detect_encoding defaults to 'ascii'. When dump_source is given
    UTF-8 bytes without a coding hint, it decodes them using 'ascii' with
    the 'replace' error handler, corrupting the characters.
    """
    output_file = tmp_path / "output.log"
    tracer = Tracer(path=str(output_file), overwrite=True)

    # Unicode source code, encoded as UTF-8 bytes, but without a `coding:` line.
    unicode_source_string = "s = '你好, world!'"
    source_bytes = [unicode_source_string.encode('utf-8')]

    # The buggy `dump_source` will call `detect_encoding`, get 'ascii', and then
    # decode the UTF-8 bytes as ascii, resulting in replacement characters.
    tracer.dump_source(source_bytes)

    # Read the content that `dump_source` wrote to the tracer's file.
    # We must read as UTF-8 to correctly interpret any replacement characters written.
    content_read = output_file.read_text(encoding="utf-8")

    # This assertion will fail on the buggy code because `content_read` will
    # contain replacement characters (e.g., "s = '������, world!'") instead of the original string.
    assert content_read == unicode_source_string, (
        f"File content was corrupted. Expected '{unicode_source_string}', got '{content_read}'"
    )
