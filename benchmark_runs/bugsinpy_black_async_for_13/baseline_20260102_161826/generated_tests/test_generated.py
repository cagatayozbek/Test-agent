import pytest
from source import tokenize_async, Token
from typing import List

def test_async_for_misclassification():
    """
    Tests that 'async' followed by 'for' is tokenized as a keyword,
    not a generic name.

    Bug: The tokenizer only creates an ('ASYNC', 'async') token when 'async'
    is followed by 'def'. In other cases, like 'async for', it incorrectly
    creates a ('NAME', 'async') token, misclassifying the keyword.
    """
    # Input tokens representing an 'async for' statement
    tokens = ["async", "for"]

    # The function returns whether it found an 'async def' and the token list
    is_async_def, result_tokens = tokenize_async(tokens)

    # The 'async' keyword should be recognized as its own token type 'ASYNC'.
    # The buggy code will incorrectly label it as 'NAME'.
    expected_tokens: List[Token] = [("ASYNC", "async"), ("NAME", "for")]

    assert not is_async_def, "'async for' should not be mistaken for 'async def'"
    assert result_tokens == expected_tokens, (
        f"'async' in 'async for' was misclassified. "
        f"Expected {expected_tokens}, but got {result_tokens}"
    )
