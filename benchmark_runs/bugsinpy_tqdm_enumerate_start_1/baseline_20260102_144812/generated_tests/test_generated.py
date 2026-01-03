import pytest
from source import tenumerate, _noop_tqdm

def test_tenumerate_start_value_is_forwarded_to_enumerate():
    """Test that the 'start' argument in tenumerate correctly sets the starting index.
    
    Bug: 'start' is incorrectly passed to tqdm_class instead of enumerate.
    """
    test_iterable = ['item1', 'item2', 'item3']
    custom_start_value = 5

    # Call tenumerate with a custom start value
    enumerated_items = list(tenumerate(test_iterable, start=custom_start_value))

    # The first item's index should be custom_start_value, not 0
    # On buggy code, this will be (0, 'item1'). On fixed code, it will be (5, 'item1').
    assert len(enumerated_items) == len(test_iterable), (
        f"Expected {len(test_iterable)} items, but got {len(enumerated_items)}."
    )

    first_index, first_value = enumerated_items[0]

    assert first_index == custom_start_value, (
        f"Expected first index to be {custom_start_value} (from 'start' argument), "
        f"but got {first_index}. This indicates 'start' was ignored by enumerate."
    )
    assert first_value == 'item1', "First value in iterable should remain 'item1'."

    # Also check a subsequent index to ensure enumeration continued correctly from 'start'
    second_index, second_value = enumerated_items[1]
    assert second_index == custom_start_value + 1, (
        f"Expected second index to be {custom_start_value + 1}, but got {second_index}."
    )
    assert second_value == 'item2', "Second value in iterable should remain 'item2'."
