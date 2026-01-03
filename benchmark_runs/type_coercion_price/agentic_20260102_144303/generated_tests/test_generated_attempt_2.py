import pytest
from source import filter_expensive_items

def test_filter_expensive_items_with_string_price_type_error():
    """Test that filter_expensive_items raises TypeError with string prices on buggy code.
    
    Bug: Directly comparing string 'price' with an integer 'threshold' causes a TypeError.
    """
    items = [
        {'name': 'Laptop', 'price': 1200},
        {'name': 'Monitor', 'price': '300'},
        {'name': 'Keyboard', 'price': 75},
        {'name': 'Mouse', 'price': '50'}
    ]
    threshold = 150

    # On buggy code, calling filter_expensive_items will raise a TypeError
    # because '300' > 150 is an invalid comparison in Python 3.
    # On fixed code (e.g., converting price to int), it should return:
    expected_result = [
        {'name': 'Laptop', 'price': 1200},
        {'name': 'Monitor', 'price': '300'}
    ]

    filtered_items = filter_expensive_items(items, threshold)

    assert filtered_items == expected_result, (
        f"Expected to filter items above {threshold}, but got {filtered_items}. "
        f"This assert will only be reached if no TypeError is raised before it."
    )