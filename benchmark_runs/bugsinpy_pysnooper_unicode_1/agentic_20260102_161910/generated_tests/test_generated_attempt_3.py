import pytest
from source import Tracer

def test_non_ascii_source_corruption_without_coding_declaration(tmp_path):
    """
    Tests that non-ASCII source code without a 'coding:' declaration
    is corrupted by `dump_source`.

    The bug is that `detect_encoding` defaults to 'ascii', causing `dump_source`
    to decode valid UTF-8 bytes incorrectly, replacing non-ASCII characters.
    """
    # A string with a non-ASCII character (smart quote: ’)
    original_source = "value = 'python’s best'"

    # The source code as UTF-8 bytes, without a 'coding:' declaration
    source_bytes = [original_source.encode('utf-8')]

    # Setup the tracer to write to a temporary file
    output_file = tmp_path / "test_output.py"
    tracer = Tracer(path=str(output_file))

    # Call the method under test. It returns the string that it attempts to write.
    rendered_string = tracer.dump_source(source_bytes)

    # On the buggy version:
    # 1. detect_encoding() incorrectly returns 'ascii'.
    # 2. b"value = 'python\xe2\x80\x99s best'".decode('ascii', 'replace') is called.
    # 3. This produces "value = 'python\ufffds best'" (with a replacement char).
    # 4. The assertion fails because the strings do not match.
    # On the fixed version, encoding would default to utf-8, and the string would be correct.
    assert rendered_string == original_source, (
        f"Non-ASCII source was corrupted during processing. "
        f"Expected: '{original_source}', Got: '{rendered_string}'"
    )
