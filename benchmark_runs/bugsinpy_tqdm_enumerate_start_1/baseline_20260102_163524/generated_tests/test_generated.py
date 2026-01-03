import pytest
from source import tenumerate

def test_tenumerate_respects_start_parameter():
    """
    Tests that tenumerate correctly uses the `start` parameter for enumeration.

    The bug is that the `start` parameter is incorrectly passed to the
    `tqdm_class` instead of the `enumerate` function, causing the
    enumeration to always start from 0, ignoring the provided `start` value.
    """
    data = ['a', 'b', 'c']
    start_index = 10

    # The buggy code will ignore `start=10` and produce [(0, 'a'), (1, 'b'), (2, 'c')]
    # The fixed code will respect `start=10` and produce the expected result.
    expected = [(10, 'a'), (11, 'b'), (12, 'c')]

    actual = list(tenumerate(data, start=start_index))

    assert actual == expected, (
        f"tenumerate should start counting from {start_index}, but it did not. "
        f"Expected {expected}, but got {actual}"
    )
