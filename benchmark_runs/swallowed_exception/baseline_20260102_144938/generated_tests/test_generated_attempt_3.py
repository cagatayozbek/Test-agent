import pytest
from source import process_transaction

def test_process_transaction_does_not_swallow_name_error():
    """
    Test that process_transaction does not swallow a NameError from calculate_tax
    and incorrectly return None when it should return a calculated value.

    Bug: The bare 'except:' block in process_transaction catches NameError
         (explicitly raised by calculate_tax in the buggy source) and returns None,
         masking a programming error as a data parsing issue.
    Fixed: With correct exception handling (e.g., catching only specific data errors)
           and a functional calculate_tax, process_transaction should return a
           calculated numerical value for valid input.
    """
    transaction_str = "item123:100"
    
    # Assuming in the fixed version, calculate_tax(100) would return 10 (e.g., 10% tax).
    # Then the total would be 100 (amount) + 10 (tax) = 110.
    # This value represents what a correctly functioning system would return.
    expected_fixed_result = 110 
    
    actual_result = process_transaction(transaction_str)
    
    assert actual_result == expected_fixed_result, (
        f"Expected a calculated total of {expected_fixed_result} after fixing 'calculate_tax' "
        f"and specific exception handling, but got {actual_result}. "
        "This indicates the NameError might still be swallowed, returning None instead of a proper result."
    )