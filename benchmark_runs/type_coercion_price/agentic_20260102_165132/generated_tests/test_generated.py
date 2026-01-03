import pytest
from source import filter_expensive_items

def test_filter_items_with_string_price():
    """
    Tests that filter_expensive_items can handle a string value for price
    without raising a TypeError.

    Bug: Comparing a string price (e.g., '200') with an integer threshold
    raises a TypeError in the buggy implementation.
    """
    # Setup: A list of items with mixed price types (int and str)
    # This input is based on the function's own docstring example.
    items_with_string_price = [
        {'name': 'Cheap Item', 'price': 50},
        {'name': 'Expensive Item (str)', 'price': '200'}
    ]
    threshold = 150

    # Expected result for the fixed code, which should handle the string price.
    expected_result = [{'name': 'Expensive Item (str)', 'price': '200'}]

    # Action: Call the function. In the buggy code, this line will raise a TypeError
    # when it tries to compare '200' > 150.
    actual_result = filter_expensive_items(items_with_string_price, threshold)

    # Assertion: This will only be reached if the code is fixed.
    # The test fails on the buggy code because the unhandled TypeError stops execution.
    assert actual_result == expected_result, (
        f"Failed to correctly filter items with string-based prices. "
        f"Expected {expected_result}, but got {actual_result}."
    )
