import pytest
from source import process_transaction

def test_process_transaction_swallows_nameerror():
    """Test that process_transaction does not swallow NameError and propagates it.

    Bug: The bare 'except:' block in process_transaction catches all exceptions,
    including NameError originating from calculate_tax, and returns None,
    masking a critical programming error.
    """
    # A valid transaction string that would normally succeed if calculate_tax worked.
    transaction_str = "item123:100"

    # The 'calculate_tax' function is designed to raise NameError in source.py.
    # We expect process_transaction to let this NameError propagate,
    # not to catch it and return None.
    with pytest.raises(NameError) as excinfo:
        process_transaction(transaction_str)

    # Optionally, verify the message if it's specific enough
    assert "name 'calculate_tax' is not defined" in str(excinfo.value),
        "Expected NameError message about 'calculate_tax' not being defined."

