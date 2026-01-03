import pytest
from source import tokenize_async


def test_async_for_tokenization():
    """Test that 'async for' is correctly tokenized.

    Bug: The 'async' keyword is dropped before 'for', leading to incorrect tokenization.
    """
    tokens = ["async", "for", "item", "in", "items"]  # Minimal async for comprehension
    async_def, result = tokenize_async(tokens)

    # In the buggy version, 'async' is dropped or mis-tokenized.
    # In the fixed version, 'async' should be present as a token.

    assert any(t[0] == 'ASYNC' for t in result), "'async' keyword should be tokenized as ASYNC"
    assert ('NAME', 'for') in result, "'for' should be present in the tokens"

    # Check for the specific tokens.
    expected_tokens = [('ASYNC', 'async'), ('NAME', 'for'), ('NAME', 'item'), ('NAME', 'in'), ('NAME', 'items')]
    assert result == expected_tokens
