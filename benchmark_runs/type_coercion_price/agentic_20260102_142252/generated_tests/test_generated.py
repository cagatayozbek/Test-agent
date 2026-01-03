import pytest
from source import filter_expensive_items


def test_type_error_price():
    """Test that a TypeError is raised when comparing string price to integer threshold.

    Bug: The code attempts to compare a string price with an integer threshold, resulting in a TypeError.
    """
    items = [{'name': 'A', 'price': '200'}, {'name': 'B', 'price': 100}]
    threshold = 150
    with pytest.raises(TypeError):
        filter_expensive_items(items, threshold)
