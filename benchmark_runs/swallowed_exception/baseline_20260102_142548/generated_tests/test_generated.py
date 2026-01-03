import pytest
from source import process_transaction


def test_name_error_swallowed():
    """Test that NameError is swallowed by the bare except block.

    Bug: The bare except block catches and hides the NameError, causing
    the function to return None instead of raising an exception.
    """
    transaction_str = "item_1:100"
    result = process_transaction(transaction_str)
    assert result is None, \
        "Expected None due to swallowed NameError, but got a different result."
