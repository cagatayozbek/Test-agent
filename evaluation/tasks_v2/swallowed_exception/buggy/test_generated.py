import pytest
from source import process_transaction

def test_bare_except_does_not_swallow_name_error():
    """
    Tests that a programming error (NameError) is not swallowed by the bare 'except:'.

    Bug: A bare 'except:' block catches all exceptions, including NameError,
    hiding a programming error and making it seem like a data format issue
    by returning None. The fix should be to use a more specific exception
    handler (e.g., `except (ValueError, IndexError):`), which would let the
    NameError propagate.
    """
    # This input string is syntactically valid and should not cause a
    # ValueError or IndexError. Its purpose is to reach the line that
    # calls the missing function.
    valid_transaction_str = "item123:100"

    # The buggy code will swallow the NameError from the call to `calculate_tax`
    # and return None. This will cause pytest.raises to fail the test because
    # the expected exception was not raised.
    # The fixed code will not catch the NameError, allowing it to be raised,
    # which will cause this test to pass.
    with pytest.raises(NameError, match="name 'calculate_tax' is not defined"):
        process_transaction(valid_transaction_str)