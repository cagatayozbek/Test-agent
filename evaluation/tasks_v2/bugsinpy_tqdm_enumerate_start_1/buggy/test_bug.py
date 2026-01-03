import pytest
from source import tenumerate

def test_tenumerate_ignores_start_argument():
    """
    Tests that tenumerate fails to use the `start` argument for enumeration.

    Bug: The `start` argument is incorrectly passed to the tqdm_class constructor
    instead of to the `enumerate` call, so the enumeration index always starts at 0.
    """
    test_iterable = ['a', 'b', 'c']
    start_index = 10

    # The buggy function will ignore start=10 and produce [(0, 'a'), (1, 'b'), (2, 'c')]
    result = list(tenumerate(test_iterable, start=start_index))

    # The correct behavior is to start enumeration from start_index
    expected_result = [(10, 'a'), (11, 'b'), (12, 'c')]

    assert result == expected_result, (
        f"tenumerate should have started counting from {start_index}, but it didn't. "
        f"Expected: {expected_result}, Got: {result}"
    )