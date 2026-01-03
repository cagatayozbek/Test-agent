import pytest
from source import process_transaction

def test_process_transaction_propagates_name_error():
    """Test that process_transaction does not swallow a NameError.
    
    Bug: A bare 'except:' block catches ALL exceptions, including NameError
    from missing internal functions, returning None instead of propagating the error.
    """
    transaction_str = "item_id_123:500"

    # In the buggy code:
    # 1. `process_transaction` calls `calculate_tax`.
    # 2. `calculate_tax` (as defined in buggy source.py) explicitly raises NameError.
    # 3. The bare `except:` block in `process_transaction` catches this NameError.
    # 4. `process_transaction` returns None.
    # The `pytest.raises(NameError)` context manager will NOT catch a NameError 
    # because the function returns None instead of raising it. This will cause the test to FAIL.

    # In the fixed code (assuming the bare `except:` is removed or made specific, 
    # and `calculate_tax` still raises NameError as per its definition):
    # 1. `process_transaction` calls `calculate_tax`.
    # 2. `calculate_tax` raises NameError.
    # 3. The NameError propagates out of `process_transaction`.
    # 4. The `pytest.raises(NameError)` context manager WILL catch the NameError. This will cause the test to PASS.
    
    with pytest.raises(NameError) as excinfo:
        process_transaction(transaction_str)

    assert "name 'calculate_tax' is not defined" in str(excinfo.value),
        "The NameError message should indicate that 'calculate_tax' is undefined."