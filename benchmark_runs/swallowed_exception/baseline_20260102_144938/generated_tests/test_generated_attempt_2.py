import pytest
from source import process_transaction

def test_name_error_not_swallowed_by_bare_except():
    """Test that NameError from an undefined function call is not swallowed
    by a bare 'except:' block in process_transaction, but instead propagates.
    
    Bug: The 'except:' block catches NameError and returns None, hiding the root cause.
    """
    valid_transaction_str = "item_id_123:100"

    # When process_transaction is called with valid input, it attempts to call
    # 'calculate_tax'. In the buggy scenario (as per source.py), 'calculate_tax'
    # is designed to raise a NameError. The bare 'except:' block in
    # 'process_transaction' will catch this NameError and return None, instead
    # of allowing the NameError to propagate. 
    # 
    # Therefore, on buggy code, 'pytest.raises(NameError)' will FAIL because
    # no NameError is propagated.
    # 
    # On fixed code (where the 'except:' block is either removed or refined
    # to not catch NameError), the NameError will propagate, and
    # 'pytest.raises(NameError)' will PASS.
    with pytest.raises(NameError) as excinfo:
        process_transaction(valid_transaction_str)

    # Further assert to ensure it's the expected NameError, confirming
    # the specific error message we anticipate from the 'calculate_tax' call.
    assert "name 'calculate_tax' is not defined" in str(excinfo.value), (
        "Expected 'NameError: name 'calculate_tax' is not defined' to be raised, "
        "but got a different exception message or type. "
        "This suggests the underlying NameError was not the one expected, "
        "or another error occurred."
    )