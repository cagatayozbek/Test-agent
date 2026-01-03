import pytest
from source import process_transaction

def test_nameerror_propagation_on_critical_bug():
    """Test that a NameError from a missing function is not silently swallowed.

    Bug: The process_transaction function has a bare 'except:' block that
    catches a NameError originating from calculate_tax, causing it to return
    None instead of letting the critical NameError propagate.
    """
    # Use a valid transaction string to ensure input parsing doesn't cause
    # a ValueError, allowing the code to reach the calculate_tax call.
    transaction_input = "item_id_123:100"

    # We expect a NameError to propagate because a missing function definition
    # is a critical application error that should not be handled gracefully
    # by returning None.
    # On buggy code, process_transaction will catch NameError and return None.
    # Therefore, pytest.raises(NameError) will FAIL because NameError does not propagate.
    # On fixed code (without the bare except swallowing NameError), NameError WILL propagate,
    # and pytest.raises(NameError) will PASS.
    with pytest.raises(NameError) as excinfo:
        process_transaction(transaction_input)

    # Further assert that the propagated NameError has the expected message
    # to confirm it's the specific bug we're targeting.
    assert "name 'calculate_tax' is not defined" in str(excinfo.value),
        "Expected NameError message about 'calculate_tax' not being defined."
