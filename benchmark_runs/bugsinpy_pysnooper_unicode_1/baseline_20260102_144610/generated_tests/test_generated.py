import pytest
import os
import tempfile
from source import Tracer

def test_tracer_writes_unicode_correctly_to_file():
    """Test that Tracer correctly writes unicode characters to a file, specifying UTF-8 encoding to avoid corruption.

    Bug: Tracer.write method (and implicitly dump_source using it) does not specify
    encoding='utf-8' when opening files, leading to corruption of non-ASCII characters
    if the platform's default encoding is not UTF-8.
    """
    temp_file_path = None
    try:
        # Create a temporary file to simulate the output log file
        # mkstemp creates and opens the file. We close its descriptor immediately
        # so Tracer can open it later by path.
        fd, temp_file_path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)

        tracer = Tracer(path=temp_file_path, overwrite=True)

        # Define source bytes containing a Unicode character (UTF-8 encoded 'é').
        # We also include a 'coding: utf-8' declaration in the source
        # to ensure the detect_encoding function (called by dump_source)
        # correctly identifies the source's encoding. This ensures that
        # dump_source produces the correct Unicode string *before* the write operation,
        # thereby isolating the bug to the file writing step itself.
        source_content_bytes = [
            b'# -*- coding: utf-8 -*-\n',
            b'line_with_unicode = "h\xc3\xa9llo World!"\n' # 'é' is U+00E9, UTF-8 encoded as C3 A9
        ]
        expected_decoded_string = '# -*- coding: utf-8 -*-\nline_with_unicode = "héllo World!"\n'

        # Use dump_source to process and write the content.
        # This method calls detect_encoding, decodes bytes to a string,
        # and then calls Tracer.write to persist it to the file.
        rendered_content = tracer.dump_source(source_content_bytes)

        # Assert that dump_source's internal processing (decoding and rendering)
        # yields the correct Unicode string before attempting to write.
        assert rendered_content == expected_decoded_string, \
            "dump_source internal decoding/rendering failed before file write."

        # Read the file back, explicitly using UTF-8 encoding.
        # This is the crucial step that will reveal the bug. If Tracer.write
        # did not specify 'encoding='utf-8'', the non-ASCII characters may have
        # been corrupted during the write operation (e.g., encoded with a platform default).
        with open(temp_file_path, 'r', encoding='utf-8') as f:
            read_content = f.read()

        # Assert that the content read from the file matches the expected Unicode string.
        # If the bug is present, this assertion will fail because of corruption
        # or a UnicodeDecodeError during the read, as the bytes written won't be
        # valid UTF-8 for the 'é' character if the default encoding was used.
        assert read_content == expected_decoded_string, \
            f"Unicode content corrupted during file write/read cycle. " \
            f"Expected:\n---\n'{expected_decoded_string}'\n---\nGot:\n---\n'{read_content}'\n---"

    finally:
        # Clean up the temporary file, regardless of test outcome.
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
