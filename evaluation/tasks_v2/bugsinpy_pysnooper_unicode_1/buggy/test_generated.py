import pytest
from pathlib import Path
from source import Tracer

def test_dump_source_with_unicode_no_coding_declaration(tmp_path: Path):
    """
    Tests that Tracer.dump_source correctly handles unicode in source
    bytes when no explicit 'coding' declaration is present.

    The bug has two parts:
    1. detect_encoding defaults to 'ascii' instead of a safer 'utf-8'.
    2. Tracer.write does not specify 'utf-8' encoding, risking corruption.

    This test provides source bytes containing a UTF-8 character (😊)
    without a '# coding: utf-8' comment. The buggy code will decode it as
    'ascii' with replacements, corrupting the character, causing the test to fail.
    """
    output_file = tmp_path / "dumped_source.py"

    # Source code with a unicode character, encoded in UTF-8, but without a
    # "coding: utf-8" pragma. This forces the buggy default.
    unicode_char = "😊"
    expected_content = f"# A comment with unicode: {unicode_char}\n"
    source_bytes_list = [expected_content.encode('utf-8')]

    # Instantiate the tracer
    tracer = Tracer(path=str(output_file), overwrite=True)

    # Dump the source. In the buggy version:
    # 1. detect_encoding() returns 'ascii'.
    # 2. .decode('ascii', 'replace') corrupts the unicode_char.
    # 3. .write() may fail or write corrupted data depending on platform.
    tracer.dump_source(source_bytes_list)

    # Read the file back with explicit UTF-8 encoding to check its content.
    # This is crucial for verifying the integrity of the written data.
    content_read = output_file.read_text(encoding='utf-8')

    assert content_read == expected_content, (
        "The content written to the file was corrupted due to incorrect encoding. "
        f"Expected: {expected_content!r}, Got: {content_read!r}"
    )
