import pytest
from source import filter_expensive_items

def test_filter_with_string_price_type_error():
    """Tests that filter_expensive_items handles string prices without a TypeError.

    Bug: The code compares a string-based price with an integer threshold, e.g., '200' > 150,
    which raises a TypeError in Python 3.
    """
    # A mix of items with integer and string prices to test the buggy comparison
    items = [
        {'name': 'Cheap', 'price': 50},
        {'name': 'Expensive String', 'price': '200'},  # This will cause the TypeError
        {'name': 'Borderline', 'price': 150}
    ]
    threshold = 160

    # The expected output if the string '200' is correctly coerced and compared
    expected = [{'name': 'Expensive String', 'price': '200'}]

    # In the buggy code, this function call will raise a TypeError and fail the test.
    # In the fixed code, it should run without error and return the correct list.
    result = filter_expensive_items(items, threshold)

    assert result == expected, (
        f"Failed to filter items with string prices correctly. "
        f"Expected {expected}, but got {result}."
    )