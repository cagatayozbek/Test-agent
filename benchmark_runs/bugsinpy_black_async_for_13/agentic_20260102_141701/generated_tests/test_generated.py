import pytest
from source import tokenize_async


def test_async_for_tokenization():
    """Test that 'async for' is correctly tokenized.

    Bug: The tokenizer drops the 'async' keyword before 'for'.
    """
    tokens = ["async", "for", "item", "in", "items"]  # Example of async for loop
    async_def, results = tokenize_async(tokens)

    # Expect 'async' to be emitted as a NAME token and 'for' as a NAME token.
    expected_results = [("NAME", "async"), ("NAME", "for"), ("NAME", "item"), ("NAME", "in"), ("NAME", "items")]

    assert results == expected_results, f"Expected {expected_results}, but got {results}"
    assert async_def == False, "async_def should be False for async for loop"
