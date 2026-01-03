import pytest
import locale
from pathlib import Path
from source import Tracer

def test_tracer_write_corrupts_unicode_on_non_utf8_systems(tmp_path: Path, monkeypatch):
    """
    Tests that Tracer.write fails when writing unicode characters on a system
    with a non-UTF-8 default encoding.

    The bug is that `open()` is called without specifying `encoding='utf-8'`,
    causing it to use the system's default encoding. This test simulates such a
    system by monkeypatching the default encoding to 'ascii'.
    """
    # 1. Setup: A non-ASCII string and a temporary file path
    unicode_string = "résumé: Привет мир 😊"
    output_file = tmp_path / "tracer_output.log"

    # 2. Simulate a non-UTF-8 environment (the condition that triggers the bug).
    #    The `open()` built-in uses `locale.getpreferredencoding()` to find the
    #    default encoding on the system.
    monkeypatch.setattr(locale, 'getpreferredencoding', lambda do_setlocale=True: 'ascii')

    # 3. Instantiate the Tracer and call the buggy method
    tracer = Tracer(path=str(output_file))
    
    # On the buggy code, this `write` call will raise a UnicodeEncodeError
    # because the default encoding is now 'ascii', which cannot handle the string.
    # On the fixed code, it will use the hardcoded 'utf-8' and succeed.
    tracer.write(unicode_string)

    # 4. Assert: Verify the file content. This part will only be reached on the
    #    fixed code, confirming the fix works as expected.
    #    The file must be read back with 'utf-8' to correctly interpret the data.
    content_read = output_file.read_text(encoding='utf-8')
    assert content_read == unicode_string, (
        "The content written to the file does not match the original unicode string. "
        "It might have been corrupted due to incorrect encoding."
    )