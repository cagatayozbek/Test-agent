import pytest
from source import process_batch

def test_process_batch_includes_last_element():
    """Test that process_batch processes all elements, including the last one.

    Bug: The loop `range(len(items) - 1)` causes the last item in the list
    to be skipped during processing.
    """
    # Arrange: A list with multiple items
    test_items = [10, 20, 30]
    
    # The expected result if all items are processed (10*2, 20*2, 30*2)
    expected_result = [20, 40, 60]

    # Act: Process the batch
    actual_result = process_batch(test_items)

    # Assert: The actual result must match the expected result.
    # The buggy code will return [20, 40], failing this assertion.
    assert actual_result == expected_result, (
        f"The last element of the list was not processed. "
        f"Expected {expected_result}, but got {actual_result}."
    )