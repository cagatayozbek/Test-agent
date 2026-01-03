import pytest
from source import process_batch


def test_process_batch_last_element():
    """Test that process_batch processes the last element in the list.

    Bug: The loop in process_batch stops one element short, skipping the last item.
    """
    items = [1, 2, 3, 4]
    expected_results = [2, 4, 6, 8]
    actual_results = process_batch(items)
    assert actual_results == expected_results, \
        f"Expected {expected_results}, but got {actual_results}. The last element was not processed."
