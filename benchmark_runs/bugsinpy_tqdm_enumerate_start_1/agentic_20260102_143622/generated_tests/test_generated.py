import pytest
from source import tenumerate, _noop_tqdm

def test_tenumerate_custom_start_ignored():
    """Test that tenumerate correctly applies a custom 'start' index.
    
    Bug: 'start' argument is passed to `tqdm_class` instead of `enumerate`,
    causing enumerate to always start from 0.
    """
    sample_iterable = ['item1', 'item2', 'item3']
    custom_start_value = 10

    # Call tenumerate with a custom start value and the no-op tqdm class
    # The buggy code will ignore `custom_start_value` for enumerate.
    enumerated_list = list(tenumerate(sample_iterable, start=custom_start_value, tqdm_class=_noop_tqdm))

    # Expected result if bug is fixed: [(10, 'item1'), (11, 'item2'), (12, 'item3')]
    # Actual result with bug:          [(0, 'item1'), (1, 'item2'), (2, 'item3')]

    # Assert that the first index matches the custom_start_value
    assert enumerated_list[0][0] == custom_start_value, (
        f"Expected first index to be {custom_start_value}, "
        f"but got {enumerated_list[0][0]}. The 'start' argument was ignored." 
    )

    # Assert other indices increment correctly from the custom_start_value
    assert enumerated_list[1][0] == custom_start_value + 1
    assert enumerated_list[2][0] == custom_start_value + 2
