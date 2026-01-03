import pytest
from source import process_transaction

def test_bare_except_swallows_name_error():
    """
    Tests that a NameError from a dependency is not swallowed by a bare except.

    The buggy `process_transaction` uses 'except:' which catches the NameError
    from the (intentionally broken) `calculate_tax` function and incorrectly
    returns None, masking a critical programming error as a data parsing issue.
    A programming error like NameError should propagate.
    """
    # This input is valid, so no ValueError or IndexError should occur.
    # The only exception should be the NameError from calculate_tax.
    valid_input = "item-abc:100"

    # This test asserts that a NameError IS raised and propagates out.
    # The buggy code will swallow the exception and return None, causing this
    # `pytest.raises` context manager to fail because the expected exception was not seen.
    with pytest.raises(NameError, match="name 'calculate_tax' is not defined"):
        process_transaction(valid_input)
