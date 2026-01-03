import pytest
from source import process_transaction

def test_internal_name_error_is_not_swallowed():
    """
    Tests that a programming error (NameError) inside process_transaction
    is not swallowed by the generic exception handler.

    The bug is a bare `except:` that catches all exceptions, including
    NameError, and incorrectly returns None, masking the real bug.
    """
    # This input is syntactically valid and should not cause a data-related exception.
    # It will, however, trigger the code path with the internal NameError.
    valid_input = "item:100"

    # We assert that a NameError MUST be raised and propagated.
    # On the buggy code, the bare `except:` will catch the NameError and return None,
    # so pytest.raises will fail, revealing the bug.
    # On the fixed code (e.g., `except (ValueError, IndexError):`), the NameError
    # will not be caught and will propagate, causing the test to pass.
    with pytest.raises(NameError, match="name 'calculate_tax' is not defined"):
        process_transaction(valid_input)