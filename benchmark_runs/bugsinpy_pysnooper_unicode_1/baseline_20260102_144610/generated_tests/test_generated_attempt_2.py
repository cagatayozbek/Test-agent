import pytest
import tempfile
import os
# CRITICAL: import from source.py
from source import Tracer

# Store original built-in open for use in the mock
_original_open = open

@pytest.fixture
def mock_corrupting_open_for_tracer(monkeypatch):
    """
    Monkeypatch builtins.open to simulate an environment where the default
    encoding for files (when not explicitly specified) is ASCII with
    'replace' error handling. This setup is designed to force the buggy
    behavior of 'Tracer.write' to corrupt non-ASCII characters.

    If 'encoding' is explicitly passed to open (as it would be in the fixed code),
    the mock will not interfere.
    """
    def mocked_open(*args, **kwargs):
        # If the caller (Tracer.write in its buggy state) does NOT specify an encoding,
        # we simulate a problematic default (e.g., ASCII with character replacement).
        if 'encoding' not in kwargs:
            kwargs['encoding'] = 'ascii'
            kwargs['errors'] = 'replace' # This simulates corruption by replacing unencodable chars with '?'
        
        # Use the original open function with potentially modified kwargs
        return _original_open(*args, **kwargs)

    # Apply the mock to builtins.open for the duration of the test
    monkeypatch.setattr("builtins.open", mocked_open)

def test_tracer_writes_unicode_corrupted_without_utf8(mock_corrupting_open_for_tracer):
    """
    Test that Tracer.write corrupts non-ASCII characters when its underlying
    file write operation does not explicitly specify UTF-8 encoding.

    Bug: The Tracer.write method relies on the platform's default encoding.
         If this default is not UTF-8 (simulated here as ASCII with 'replace'
         error handling), non-ASCII characters are corrupted. The test asserts
         that the content read back matches the original Unicode string, which
         will fail if corruption occurs.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "snoop_output.txt")
        tracer = Tracer(file_path)

        # A string containing non-ASCII characters that cannot be represented
        # in plain ASCII and would be replaced by '?' if 'errors=replace' is active.
        unicode_string = "Snoopy says: æøåéüñ"

        # The buggy Tracer.write will call open() without an 'encoding' argument.
        # Our `mock_corrupting_open_for_tracer` fixture will then intercept this
        # and force open() to use 'ascii' encoding with 'errors=replace'.
        tracer.write(unicode_string)

        # Read the file back explicitly as UTF-8 to check for the original content.
        # On the buggy code (with our mock active), the file would contain corrupted
        # characters (e.g., '?' for 'æøåéüñ'). When read back as UTF-8, it would
        # yield 'Snoopy says: ??????' or similar, which will not match `unicode_string`.
        # On the fixed code, Tracer.write would specify `encoding='utf-8'`, bypassing
        # the mock's forced ASCII, and the file would contain correct UTF-8 bytes.
        with _original_open(file_path, 'r', encoding='utf-8') as f_read:
            read_content = f_read.read()

        assert read_content == unicode_string, (
            f"File content should be the original unicode string '{unicode_string}', "
            f"but it was corrupted to '{read_content}' (likely due to missing UTF-8 encoding specification in Tracer.write)."
        )
