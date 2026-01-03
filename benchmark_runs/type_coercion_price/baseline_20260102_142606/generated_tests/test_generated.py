import pytest
from source import filter_expensive_items


def test_string_price_comparison():
    """Test that string price is correctly handled, avoiding TypeError.

    Bug: Comparing string price with integer threshold raises TypeError.
    """
    items = [{'name': 'A', 'price': '200'}, {'name': 'B', 'price': 100}]
    threshold = 150
    
    # Expect item A to be filtered since '200' should be treated like an integer and thus greater than 150
    result = filter_expensive_items(items, threshold)
    
    assert result == [{'name': 'A', 'price': '200'}] , "Should filter item with string price greater than threshold"
