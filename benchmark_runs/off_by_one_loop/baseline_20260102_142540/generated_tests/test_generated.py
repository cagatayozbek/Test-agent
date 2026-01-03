import pytest
from source import process_batch


def test_process_batch_last_item():
    """Test that the last item in the list is processed correctly.
    
    Bug: The loop excludes the last item due to incorrect range calculation.
    """
    items = [1, 2, 3]
    expected_results = [2, 4, 6]
    
    results = process_batch(items)
    
    assert results == expected_results, \
        f"Last item was not processed. Expected {expected_results}, got {results}"
