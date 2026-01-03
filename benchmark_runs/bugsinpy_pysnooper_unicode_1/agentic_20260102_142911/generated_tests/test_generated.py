import pytest
from pathlib import Path

from source import Tracer, detect_encoding

def test_tracer_writes_unicode_output_correctly(tmp_path: Path):
    """
    Test that Tracer correctly writes non-ASCII (unicode) characters
    to the output file without corruption, explicitly handling UTF-8 encoding.

    The bug manifests when Tracer.write calls open() without specifying 'encoding="utf-8"',
    leading to the use of a platform-dependent default encoding (e.g., ASCII or cp1252),
    which corrupts non-ASCII characters on write.
    """
    # Define source lines including a UTF-8 encoding declaration
    # and a non-ASCII character ('你好' - "ni hao" in Chinese)
    # The bytes representation includes the UTF-8 encoding for '你好'
    source_lines_bytes = [
        b'# coding: utf-8\n',
        b'print("This is a unicode string: \xe4\xbd\xa0\xe5\xa5\xbd")\n' # '你好' in UTF-8 bytes
    ]
    
    # The expected content that should be written to the file
    expected_output_string = (
        '# coding: utf-8\n'
        'print("This is a unicode string: 你好")\n'
    )

    # Path for the tracer's output file within the temporary directory
    output_file = tmp_path / "trace_output.txt"

    # Instantiate the Tracer with the output file path
    tracer = Tracer(str(output_file))

    # Simulate dumping source code with unicode characters
    # This process involves detect_encoding and then Tracer.write.
    # The detect_encoding method is expected to return "utf-8" for the given source.
    # The dump_source method correctly decodes to a unicode string (`rendered`).
    # The bug lies in `Tracer.write` failing to use UTF-8 when writing `rendered` to file.
    tracer.dump_source(source_lines_bytes)

    # Read the content of the output file, explicitly specifying UTF-8 encoding.
    # This is crucial for correctly interpreting the bytes that the tracer *should* have written.
    # If the tracer wrote with a different encoding, reading with 'utf-8' will either
    # raise an error or return corrupted characters, causing the assertion to fail.
    actual_output_string = output_file.read_text(encoding='utf-8')

    # Assert that the content written by the tracer is identical to the expected
    # unicode string, confirming no corruption occurred.
    assert actual_output_string == expected_output_string, (
        "Unicode characters were corrupted during file write. "
        "Expected correct UTF-8 output but got different content."
    )