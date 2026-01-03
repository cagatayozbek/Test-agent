from source import tenumerate


def test_tenumerate_start_index():
    """Test that tenumerate respects the start index.

    Bug: tenumerate forwards start to tqdm_class instead of enumerate,
    so the starting index is ignored and counts are shifted.
    """
    data = ['a', 'b', 'c']
    expected_indices = [5, 6, 7]
    actual_indices = []

    for i, _ in tenumerate(data, start=5):
        actual_indices.append(i)

    assert actual_indices == expected_indices, \
        f"tenumerate should start at 5, but got {actual_indices}"