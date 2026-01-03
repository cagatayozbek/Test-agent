from source import tenumerate


def test_tenumerate_start_index():
    """Test that tenumerate correctly uses the start index.\n    \n    Bug: The start argument is passed to tqdm_class instead of enumerate,\n    causing the enumeration to always start from 0 regardless of the start value.\n    """
    data = ['a', 'b', 'c']
    start_index = 5
    
    # Enumerate should start at index 5, not 0.
    enumerated_data = list(tenumerate(data, start=start_index))

    # Assert that the first element's index is correct.
    assert enumerated_data[0][0] == start_index, \
        f"Expected start index to be {start_index}, but got {enumerated_data[0][0]}"
