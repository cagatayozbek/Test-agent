import pytest
import tempfile
import os
from source import Tracer

def test_tracer_write_unicode_corruption():
    """
    Test that Tracer.write correctly handles non-ASCII UTF-8 characters.

    Bug: Tracer.write relies on the platform's default encoding, which can lead
    to corruption of non-ASCII characters when the default is not UTF-8 (e.g., ASCII).
    This test is designed to fail if run in an environment where `open()` defaults
    to a non-UTF-8 encoding (e.g., if `PYTHONIOENCODING='ascii'` or 'latin1'
    is set externally for the test run).
    """
    original_text = "Hello, world! This is a test with non-ASCII characters: café, 你好, über."
    
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "trace_output.txt")
        tracer = Tracer(path=file_path, overwrite=True)
        
        # 1. Write the text using the buggy/fixed Tracer
        try:
            tracer.write(original_text)
        except UnicodeEncodeError as e:
            pytest.fail(
                f"Tracer.write raised UnicodeEncodeError, indicating default encoding "
                f"could not handle non-ASCII characters. Bug revealed: {e}"
            )
        
        # 2. Read the content back explicitly as UTF-8 to check for corruption
        read_text = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                read_text = f.read()
        except UnicodeDecodeError as e:
            pytest.fail(
                f"Failed to read file with UTF-8 encoding. This suggests corruption "
                f"during write or an invalid byte sequence. Bug revealed: {e}"
            )
        
        # 3. Assert that the read content matches the original
        # This assertion should fail on buggy code if default encoding is not UTF-8
        # (e.g., it writes corrupted bytes). It should pass on fixed code.
        assert read_text == original_text, (
            f"Content mismatch: Tracer.write corrupted non-ASCII characters. "
            f"Expected '{original_text}', but got '{read_text}'. This confirms "
            f"the bug where default encoding caused incorrect byte representation."
        )
