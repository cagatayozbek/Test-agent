import pytest
from source import process_transaction

def test_bare_except_swallows_programming_error():
    """
    Tests that a NameError within the try block is not swallowed by a bare except.

    The bug is that `except:` catches all exceptions, including programming
    errors like NameError, and masks them by returning None. This test provides
    valid input that should cause a NameError to be raised due to the bug in
    the function call.

    The test asserts that a NameError MUST be raised. The buggy code will swallow
    this exception and return None, causing the test to fail with a
    `Failed: DID NOT RAISE <class 'NameError'>` message.
    """
    # This input is valid and should not cause a parsing error (e.g., ValueError).
    # It is designed to specifically trigger the internal `NameError`.
    valid_transaction_str = "item-123:100"

    # A fixed version of the code should be more specific, e.g.,
    # `except (ValueError, IndexError):`, which would let the NameError propagate.
    # This context manager asserts that a NameError must escape the function call.
    with pytest.raises(NameError):
        process_transaction(valid_transaction_str)
