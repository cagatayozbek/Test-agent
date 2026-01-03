import pytest
from source import process_transaction

def test_internal_error_is_not_swallowed():
    """
    Tests that a NameError from a dependency is not swallowed by the bare except.

    The buggy code has a `except:` block that catches all exceptions, including
    NameError, and returns None. This masks the underlying programming error.
    The fixed code should let the NameError propagate, not catch it.
    """
    # This input string is formatted correctly. Any exception raised should not be
    # a data parsing error (like ValueError or IndexError), but a logic error.
    valid_transaction_str = "item123:100"

    # We expect a NameError because calculate_tax is designed to raise it,
    # simulating a critical programming error (e.g., a missing function or typo).
    with pytest.raises(NameError, match="name 'calculate_tax' is not defined"):
        process_transaction(valid_transaction_str)

    # On the buggy code:
    # 1. process_transaction() is called.
    # 2. calculate_tax() raises a NameError.
    # 3. The bare `except:` catches the NameError.
    # 4. The function returns None instead of raising the exception.
    # 5. `pytest.raises` block fails the test because the expected NameError was never raised.
    #
    # On the fixed code:
    # 1. The more specific `except (ValueError, IndexError):` does NOT catch the NameError.
    # 2. The NameError propagates out of the function.
    # 3. `pytest.raises` catches it, and the test passes.