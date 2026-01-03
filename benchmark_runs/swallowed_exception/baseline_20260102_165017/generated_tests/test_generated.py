import pytest
from source import process_transaction

def test_bare_except_hides_name_error():
    """
    Tests that a NameError from an internal function call is not swallowed.

    Bug: A bare 'except:' catches the NameError from the call to 'calculate_tax'
    and returns None, masking the real programming error as a data processing failure.
    The test expects a NameError to be raised and propagated, but on the buggy code,
    it is swallowed, causing the test to fail because the expected exception is never raised.
    """
    # This input is perfectly valid, so any failure should be a programming error,
    # not a data validation error.
    valid_input = "item123:100"

    # On buggy code, this will fail. The `except:` block will catch the NameError,
    # process_transaction will return None, and pytest.raises will complain that
    # the expected NameError was never raised.
    # On fixed code (e.g., `except ValueError:`), the NameError will not be caught
    # and will propagate up, causing the test to pass.
    with pytest.raises(NameError, match="name 'calculate_tax' is not defined"):
        process_transaction(valid_input)
