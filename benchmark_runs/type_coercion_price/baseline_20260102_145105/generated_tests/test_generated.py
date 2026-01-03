import pytest
from source import filter_expensive_items

def test_filter_expensive_items_string_price_comparison_type_error():
    """Test that filter_expensive_items fails with TypeError when comparing string price to int threshold.
    
    Bug: Direct comparison 'str' > 'int' causes a TypeError in Python 3.
    """
    items = [
        {'name': 'Cheap Item', 'price': 50},
        {'name': 'Expensive String Price', 'price': '200'}, # This item has a string price
        {'name': 'Moderate Item', 'price': 100}
    ]
    threshold = 150

    # On the buggy code, the comparison '200' > 150 will raise a TypeError.
    # Pytest will report this uncaught exception as a test failure.

    # On fixed code, '200' would typically be converted to an integer before comparison (e.g., int('200') > 150).
    # In that case, 200 > 150 is True, so 'Expensive String Price' should be included in the result.
    expected_result = [{'name': 'Expensive String Price', 'price': '200'}]
    
    actual_result = filter_expensive_items(items, threshold)
    
    assert actual_result == expected_result, (
        f"Filter did not produce expected result after handling string prices. "
        f"Expected: {expected_result}, Got: {actual_result}"
    )
