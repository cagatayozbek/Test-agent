import pytest
from source import process_batch

def test_process_batch_includes_last_item():
    """
    Tests that the process_batch function processes the last item in the list.
    
    The bug is an off-by-one error in the loop range `range(len(items) - 1)`,
    which causes the final element of the list to be excluded from processing.
    """
    # A simple list with multiple items
    test_items = [10, 20, 30]
    
    # The expected result if all items are processed correctly
    expected_result = [20, 40, 60]
    
    # On buggy code, the loop will only process indices 0 and 1, 
    # returning [20, 40] and skipping the last item (30).
    actual_result = process_batch(test_items)
    
    assert actual_result == expected_result, (
        f"The last item in the list was not processed. "
        f"Expected {expected_result}, but got {actual_result}."
    )
