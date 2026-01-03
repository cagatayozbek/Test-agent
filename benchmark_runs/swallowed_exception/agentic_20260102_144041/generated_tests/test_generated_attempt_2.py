import pytest
from source import process_transaction

def test_process_transaction_nameerror_is_not_swallowed():
    """Test that process_transaction does not swallow NameError from calculate_tax.
    
    Bug: The bare 'except:' block in the buggy process_transaction function
    catches all exceptions, including the NameError explicitly raised by
    calculate_tax, causing process_transaction to return None instead of
    propagating the original programming error. This test asserts that a
    NameError *should* propagate.
    """
    # A valid transaction string that will trigger the call to calculate_tax
    transaction_str = "item_id:100"

    # In the buggy code:
    # 1. `process_transaction` calls `calculate_tax`.
    # 2. `calculate_tax` raises `NameError`.
    # 3. The bare `except:` block in `process_transaction` catches the `NameError`.
    # 4. `process_transaction` returns `None`.
    # Therefore, `pytest.raises(NameError)` will FAIL because no NameError is actually propagated.
    #
    # In the fixed code (e.g., if the `except:` block is removed or made more specific),
    # the `NameError` from `calculate_tax` will propagate, and `pytest.raises(NameError)`
    # will PASS.
    with pytest.raises(NameError) as excinfo:
        process_transaction(transaction_str)

    # Optionally, assert the specific message to ensure it's the NameError we expect
    assert "name 'calculate_tax' is not defined" in str(excinfo.value), \
        "Expected NameError message about 'calculate_tax' not being defined."
