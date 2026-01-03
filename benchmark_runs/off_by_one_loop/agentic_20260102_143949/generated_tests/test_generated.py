import pytest
from source import process_batch

def test_process_batch_skips_last_element():
    """Test that process_batch correctly processes ALL elements, including the last one.

    Bug: The loop `range(len(items) - 1)` causes the last element to be skipped.
    """
    # Input list with multiple elements to clearly show the skipped last element
    items = [1, 2, 3, 4, 5]
    
    # The expected result if all elements are processed correctly (multiplied by 2)
    expected_results = [2, 4, 6, 8, 10]
    
    # Call the function with the buggy code
    actual_results = process_batch(items)
    
    # Assert that the length of the results list is correct
    # This assertion will fail on buggy code (len 4 vs expected len 5)
    assert len(actual_results) == len(items), (
        f"Expected results list to have {len(items)} elements, "
        f"but got {len(actual_results)}. The last element was likely skipped."
    )
    
    # Assert that all elements, including the last, are processed correctly
    # This assertion will fail on buggy code because the last item (5*2=10) will be missing
    assert actual_results == expected_results, (
        f"Expected all items to be processed, resulting in {expected_results}, "
        f"but got {actual_results}. The last item's processing is incorrect or missing."
    )