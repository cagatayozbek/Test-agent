import pytest
from source import process_batch

def test_process_batch_skips_last_item():
    """Test that the process_batch function processes all items, including the last one.
    
    Bug: The loop `range(len(items) - 1)` incorrectly excludes the last element.
    """
    items = [10, 20, 30, 40]
    
    # Expected result if all items are processed correctly
    expected_results = [20, 40, 60, 80]
    
    actual_results = process_batch(items)
    
    # Assert that the length of the results list is correct
    assert len(actual_results) == len(items), (
        f"Expected {len(items)} items in results, but got {len(actual_results)}. "
        "The last item was likely skipped."
    )
    
    # Assert that all items were processed and match the expected values
    assert actual_results == expected_results, (
        f"Expected processed items: {expected_results}, "
        f"but got: {actual_results}. The last item's processing is missing or incorrect."
    )
