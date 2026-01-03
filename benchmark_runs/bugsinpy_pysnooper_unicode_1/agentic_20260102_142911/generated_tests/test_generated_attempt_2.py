import pytest
import os
import tempfile
from source import Tracer

def test_tracer_write_non_ascii_unicode():
    """Test that Tracer.write correctly handles non-ASCII Unicode characters.
    
    Bug: Tracer.write opens the file without specifying encoding, relying on
    platform default, which can lead to UnicodeEncodeError or silent corruption
    when writing non-ASCII characters if the default is not UTF-8.
    """
    # A string containing a 4-byte UTF-8 character (emoji) and an accented letter.
    # These are highly unlikely to be representable in non-UTF-8 default encodings
    # like ASCII, Latin-1, or cp1252 without causing an error or corruption.
    non_ascii_test_string = "Hello, world! Here's an emoji: 😂 And an accented letter: é."

    with tempfile.TemporaryDirectory() as tmpdir:
        output_filepath = os.path.join(tmpdir, "unicode_output.txt")
        
        tracer = Tracer(output_filepath, overwrite=True)
        
        # On buggy code:
        # 1. If the platform's default encoding (e.g., ASCII) cannot encode these characters,
        #    this call will raise a UnicodeEncodeError, causing the test to FAIL.
        # 2. If the platform's default encoding is a single-byte encoding (e.g., Latin-1)
        #    that incorrectly maps or replaces the characters, corrupted data will be written.
        # On fixed code: this should write correctly using explicit UTF-8.
        tracer.write(non_ascii_test_string)
        
        # Read the content back, explicitly specifying UTF-8.
        # This is the expected encoding for correctly written Unicode strings.
        # If the buggy code wrote with a different encoding or corrupted data,
        # reading with UTF-8 will likely result in a UnicodeDecodeError or
        # mismatched content.
        try:
            with open(output_filepath, 'r', encoding='utf-8') as f:
                read_content = f.read()
        except UnicodeDecodeError as e:
            pytest.fail(f"UnicodeDecodeError while reading file, indicating write corruption: {e}")
        except Exception as e:
            pytest.fail(f"An unexpected error occurred while reading the file: {e}")

        # This assertion will fail if the content was corrupted or not written correctly.
        # On fixed code, this assertion should pass.
        assert read_content == non_ascii_test_string, (
            f"Expected written content to be '{non_ascii_test_string}', "
            f"but got '{read_content}'. This indicates a potential encoding issue "
            "where non-ASCII characters were corrupted during writing due to missing encoding specification."
        )